"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Card from "@/components/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { endpoints } from "@/lib/api";
import { toast } from "@/lib/toast";

export default function ProfilePage() {
  const searchParams = useSearchParams();
  const candidateId = searchParams.get("candidate_id");

  const [profile, setProfile] = useState({
    name: "",
    email: "",
    resume_text: "",
    skills: "",
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const hasCandidateId = useMemo(
    () => Boolean(candidateId?.trim()),
    [candidateId]
  );

  useEffect(() => {
    if (!candidateId) {
      setError("Candidate ID is required to load the profile.");
      return;
    }

    let cancelled = false;

    const loadProfile = async () => {
      setLoading(true);
      setError("");

      try {
        const candidate = await endpoints.getCandidate(candidateId);

        if (cancelled) return;

        setProfile({
          name: candidate.name ?? "",
          email: candidate.email ?? "",
          resume_text: candidate.resume_text ?? "",
          skills: Array.isArray(candidate.skills)
            ? candidate.skills.join(", ")
            : "",
        });
      } catch (err) {
        if (cancelled) return;

        const message =
          err instanceof Error
            ? err.message
            : "Failed to load candidate profile";

        setError(message);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadProfile();

    return () => {
      cancelled = true;
    };
  }, [candidateId]);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setProfile((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!candidateId) {
      setError("Candidate ID is required to update the profile.");
      return;
    }

    const name = profile.name.trim();
    const email = profile.email.trim();

    if (!name) {
      toast.error("Name is required.");
      return;
    }

    if (!email) {
      toast.error("Email is required.");
      return;
    }

    const skills = profile.skills
      .split(",")
      .map((skill) => skill.trim())
      .filter(Boolean);

    setSaving(true);
    setError("");

    try {
      const updated = await endpoints.updateCandidate(candidateId, {
        name,
        email,
        resume_text: profile.resume_text.trim() || null,
        skills,
      });

      setProfile({
        name: updated.name ?? "",
        email: updated.email ?? "",
        resume_text: updated.resume_text ?? "",
        skills: Array.isArray(updated.skills)
          ? updated.skills.join(", ")
          : "",
      });

      toast.success("Profile updated successfully.");
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to update candidate profile";

      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  if (!hasCandidateId) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <Card
          title="Candidate Profile"
          description="View and update your profile information."
        >
          <div className="rounded-md border border-rose-900/40 bg-rose-950/20 p-4 text-sm text-rose-400">
            Candidate ID is missing. Open the profile page using:
            <div className="mt-2 font-mono text-xs text-zinc-300">
              /profile?candidate_id=&lt;candidate_id&gt;
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <Card
        title="Candidate Profile"
        description="View and update your name, email, resume, and skills."
      >
        {loading ? (
          <div className="py-8 text-center text-sm text-muted">
            Loading profile...
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="profile-name"
                className="mb-1 block text-sm font-medium"
              >
                Name
              </label>
              <Input
                id="profile-name"
                name="name"
                type="text"
                value={profile.name}
                onChange={handleChange}
                maxLength={200}
                required
                placeholder="Your name"
              />
            </div>

            <div>
              <label
                htmlFor="profile-email"
                className="mb-1 block text-sm font-medium"
              >
                Email
              </label>
              <Input
                id="profile-email"
                name="email"
                type="email"
                value={profile.email}
                onChange={handleChange}
                maxLength={255}
                required
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label
                htmlFor="profile-resume"
                className="mb-1 block text-sm font-medium"
              >
                Resume Text
              </label>
              <textarea
                id="profile-resume"
                name="resume_text"
                value={profile.resume_text}
                onChange={handleChange}
                maxLength={10000}
                rows={8}
                placeholder="Paste or update your resume text..."
                className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="profile-skills"
                className="mb-1 block text-sm font-medium"
              >
                Skills
              </label>
              <Input
                id="profile-skills"
                name="skills"
                type="text"
                value={profile.skills}
                onChange={handleChange}
                placeholder="Python, SQL, FastAPI, Machine Learning"
              />
              <p className="mt-1 text-xs text-muted">
                Enter skills separated by commas.
              </p>
            </div>

            {error && (
              <div className="rounded-md border border-rose-900/40 bg-rose-950/20 p-3 text-sm text-rose-400">
                {error}
              </div>
            )}

            <div className="flex justify-end">
              <Button type="submit" disabled={saving || loading}>
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}