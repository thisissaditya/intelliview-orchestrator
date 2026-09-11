import os
import random

from locust import HttpUser, between, events, task

API_TOKEN = os.environ.get("LOAD_TEST_API_KEY", "")

CREATE_CANDIDATE_PATH = "/candidates"
START_INTERVIEW_PATH = "/start-interview"
SESSION_STATUS_PATH = "/session-status/{session_id}"
ASK_QUESTION_PATH = "/interviews/ask-question"
SUBMIT_ANSWER_PATH = "/interviews/submit-answer"

MAX_ANSWERS_PER_INTERVIEW = 8

MIN_THINK_TIME = 3
MAX_THINK_TIME = 20

POST_CREATE_POLL_INTERVAL = 1.0
POST_CREATE_MAX_POLLS = 5

POSITIONS = ["Software Engineer", "Data Analyst", "Product Manager", "SRE"]
PRIORITIES = ["low", "medium", "high"]

SAMPLE_ANSWERS = [
    "I'd approach that by first clarifying the requirements, then breaking "
    "the problem into smaller pieces I can validate independently.",
    "In my last role I handled a similar situation by coordinating with "
    "stakeholders early and setting clear checkpoints.",
    "I think the tradeoff here is between speed and correctness, and I'd "
    "lean toward correctness given the stakes described.",
    "My strongest skill is probably debugging under pressure — I stay "
    "systematic instead of guessing.",
    "I'd want more context before committing to an answer, but my initial "
    "instinct is to isolate the variable and test it directly.",
]

TERMINAL_STATUSES = {"COMPLETED", "FAILED", "TIMEOUT", "CANCELLED"}


def _headers():
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["X-API-Token"] = API_TOKEN
    return headers


def _is_rate_limited(resp) -> bool:

    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", "?")
        resp.failure(f"rate_limited: 429, retry_after={retry_after}s")
        return True
    return False


class InterviewCandidate(HttpUser):

    wait_time = between(2, 6)

    def on_start(self):
        self.candidate_seq = random.randint(100000, 999999)
        self.candidate_id = None
        self.candidate_id = self._register_candidate()

    def _register_candidate(self):
        payload = {
            "name": f"Load Test Candidate {self.candidate_seq}",
            "email": f"loadtest-{self.candidate_seq}@example.com",
        }
        with self.client.post(
            CREATE_CANDIDATE_PATH,
            json=payload,
            headers=_headers(),
            name="POST /candidates (register)",
            catch_response=True,
        ) as resp:
            if _is_rate_limited(resp):
                return None
            if resp.status_code not in (200, 201):
                resp.failure(f"candidate registration failed: HTTP {resp.status_code}")
                return None
            try:
                body = resp.json()
            except ValueError:
                resp.failure("candidate registration returned non-JSON body")
                return None
            candidate_id = body.get("candidate_id") or body.get("id")
            if not candidate_id:
                resp.failure(
                    f"candidate registration response missing candidate_id "
                    f"(got keys: {list(body.keys())})"
                )
                return None
            resp.success()
            return candidate_id

    @task
    def run_full_interview(self):
        if self.candidate_id is None:

            self.candidate_id = self._register_candidate()
            if self.candidate_id is None:
                return

        session_id = self._start_interview()
        if session_id is None:
            return

        self._poll_status_after_create(session_id)

        num_answers = random.randint(
            MIN_ANSWERS_PER_INTERVIEW, MAX_ANSWERS_PER_INTERVIEW
        )
        for _ in range(num_answers):
            question_id = self._ask_question(session_id)
            if question_id is None:
                break
            self._think()
            ok = self._submit_answer(session_id, question_id)
            if not ok:
                break

        self._final_status_check(session_id)

    def _start_interview(self):
        payload = {
            "candidate_id": self.candidate_id,
            "candidate_name": f"Load Test Candidate {self.candidate_seq}",
            "position": random.choice(POSITIONS),
            "priority": random.choice(PRIORITIES),
        }
        with self.client.post(
            START_INTERVIEW_PATH,
            json=payload,
            headers=_headers(),
            name="POST /start-interview",
            catch_response=True,
        ) as resp:
            if _is_rate_limited(resp):
                return None
            if resp.status_code == 401:
                resp.failure(
                    "401 Unauthorized — check LOAD_TEST_API_KEY matches server's API_TOKEN"
                )
                return None
            if resp.status_code not in (200, 201):
                resp.failure(f"start-interview failed: HTTP {resp.status_code}")
                return None
            try:
                session_id = resp.json().get("session_id")
            except ValueError:
                resp.failure("start-interview returned non-JSON body")
                return None
            if not session_id:
                resp.failure("start-interview response missing session_id")
                return None
            resp.success()
            return session_id

    def _poll_status_after_create(self, session_id):
        import time

        path = SESSION_STATUS_PATH.format(session_id=session_id)
        for _ in range(POST_CREATE_MAX_POLLS):
            with self.client.get(
                path,
                headers=_headers(),
                name="GET /session-status/:id (post-create)",
                catch_response=True,
            ) as resp:
                if _is_rate_limited(resp):
                    return
                if resp.status_code != 200:
                    resp.failure(f"status check failed: HTTP {resp.status_code}")
                    return
                try:
                    state = resp.json().get("status", "")
                except ValueError:
                    resp.failure("status returned non-JSON body")
                    return
                resp.success()
                if state and state != "CREATED":
                    return
            time.sleep(POST_CREATE_POLL_INTERVAL)

    def _think(self):
        import time

        time.sleep(random.uniform(MIN_THINK_TIME, MAX_THINK_TIME))

    def _ask_question(self, session_id):
        payload = {"session_id": session_id}
        with self.client.post(
            ASK_QUESTION_PATH,
            json=payload,
            headers=_headers(),
            name="POST /interviews/ask-question",
            catch_response=True,
        ) as resp:
            if _is_rate_limited(resp):
                return None
            if resp.status_code == 404:
                resp.success()
                return None
            if resp.status_code != 200:
                resp.failure(f"ask-question failed: HTTP {resp.status_code}")
                return None
            try:
                question_id = resp.json().get("question_id")
            except ValueError:
                resp.failure("ask-question returned non-JSON body")
                return None
            resp.success()
            return question_id

    def _submit_answer(self, session_id, question_id):
        payload = {
            "session_id": session_id,
            "question_id": question_id,
            "answer_text": random.choice(SAMPLE_ANSWERS),
            "score": round(random.uniform(3.0, 9.5), 1),
        }
        with self.client.post(
            SUBMIT_ANSWER_PATH,
            json=payload,
            headers=_headers(),
            name="POST /interviews/submit-answer",
            catch_response=True,
        ) as resp:
            if _is_rate_limited(resp):
                return False
            if resp.status_code != 200:
                resp.failure(f"submit-answer failed: HTTP {resp.status_code}")
                return False
            resp.success()
            return True

    def _final_status_check(self, session_id):
        path = SESSION_STATUS_PATH.format(session_id=session_id)
        with self.client.get(
            path,
            headers=_headers(),
            name="GET /session-status/:id (final check)",
            catch_response=True,
        ) as resp:
            if _is_rate_limited(resp):
                pass
            elif resp.status_code != 200:
                resp.failure(f"final status check failed: HTTP {resp.status_code}")
            else:
                resp.success()


@events.quitting.add_listener
def _print_summary(environment, **kwargs):
    stats = environment.stats
    total = stats.total

    rate_limited_count = 0
    other_failure_count = 0
    for _key, err in stats.errors.items():
        occurrences = getattr(err, "occurrences", 0)
        error_text = getattr(err, "error", "") or ""
        if "rate_limited" in str(error_text):
            rate_limited_count += occurrences
        else:
            other_failure_count += occurrences

    print("\n" + "=" * 60)
    print("LOAD TEST SUMMARY")
    print("=" * 60)
    print(f"Requests:              {total.num_requests}")
    print(f"Total failures:        {total.num_failures}")
    print(f"  - rate_limited (429):{rate_limited_count}")
    print(f"  - other failures:    {other_failure_count}")
    fail_rate = (
        (total.num_failures / total.num_requests * 100) if total.num_requests else 0
    )
    other_fail_rate = (
        (other_failure_count / total.num_requests * 100) if total.num_requests else 0
    )
    print(f"Total failure rate:    {fail_rate:.2f}%")
    print(
        f"Non-rate-limit rate:   {other_fail_rate:.2f}%  <-- use THIS to judge real errors"
    )
    print(f"Median resp (ms):      {total.median_response_time}")
    print(f"95th pct (ms):         {total.get_response_time_percentile(0.95)}")
    print(f"99th pct (ms):         {total.get_response_time_percentile(0.99)}")
    print(f"Max resp (ms):         {total.max_response_time}")
    print("=" * 60)
    if rate_limited_count > 0:
        print(
            "NOTE: rate-limited requests are expected with >~60 total "
            "req/min from a single Locust host + shared API token (see "
            "RATE LIMITING section at the top of this file). They are "
            "excluded from 'Non-rate-limit rate' above."
        )

    max_acceptable_failure_rate = float(
        os.environ.get("LOAD_TEST_MAX_FAILURE_RATE", "5")
    )
    if other_fail_rate > max_acceptable_failure_rate:
        print(
            f"NON-RATE-LIMIT FAILURE RATE {other_fail_rate:.2f}% exceeds "
            f"threshold {max_acceptable_failure_rate}% — treat this run "
            f"as a failed test."
        )
