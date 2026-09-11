describe("Issue #8 - Camera and Microphone Browser Compatibility", () => {
  const candidateId = "cand-issue-8";
  const sessionId = "session-issue-8";

  const mockMedia = (win, shouldReject = false) => {
    const audioTrack = {
      kind: "audio",
      enabled: true,
      stop: cy.stub(),
    };

    const videoTrack = {
      kind: "video",
      enabled: true,
      stop: cy.stub(),
    };

    const stream = {
      getAudioTracks: () => [audioTrack],
      getVideoTracks: () => [videoTrack],
      getTracks: () => [audioTrack, videoTrack],
    };

    const getUserMedia = shouldReject
      ? cy.stub().rejects(
          new DOMException("Permission denied", "NotAllowedError")
        )
      : cy.stub().resolves(stream);

    Object.defineProperty(win.navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia },
    });

    class MockAudioContext {
      createMediaStreamSource() {
        return {
          connect() {},
        };
      }

      createAnalyser() {
        return {
          fftSize: 64,
          frequencyBinCount: 32,
          getByteFrequencyData() {},
        };
      }

      close() {
        return Promise.resolve();
      }
    }

    win.AudioContext = MockAudioContext;
    win.webkitAudioContext = MockAudioContext;
  };

  beforeEach(() => {
    cy.intercept("POST", "**/start-interview", {
      statusCode: 200,
      body: {
        session_id: sessionId,
        status: "QUEUED",
        created_at: "2026-09-07T12:00:00Z",
        candidate_id: candidateId,
        risk_score: null,
        estimated_wait_time: 0,
      },
    }).as("startInterview");
  });

  it("supports camera and microphone access during interview startup", () => {
    cy.visit("http://localhost:3000/interview", {
      onBeforeLoad(win) {
        win.localStorage.setItem("api_token", "test-jwt-token");
        mockMedia(win);
      },
    });

    cy.contains("Live Interview").should("be.visible");

    cy.get('input[placeholder="cand-1234"]')
      .should("be.visible")
      .type(candidateId);

    cy.contains("button", "Start Interview")
      .should("not.be.disabled")
      .click();

    cy.wait("@startInterview");

    cy.contains("LIVE").should("be.visible");
    cy.contains(sessionId).should("be.visible");
  });

  it("handles camera and microphone permission denial without crashing", () => {
    cy.visit("http://localhost:3000/interview", {
      onBeforeLoad(win) {
        win.localStorage.setItem("api_token", "test-jwt-token");
        mockMedia(win, true);
      },
    });

    cy.contains("Live Interview").should("be.visible");

    cy.get('input[placeholder="cand-1234"]')
      .should("be.visible")
      .type(candidateId);

    cy.contains("button", "Start Interview")
      .should("not.be.disabled")
      .click();

    cy.wait("@startInterview");

    cy.contains("Live Interview").should("be.visible");
  });

  it("exposes the required browser media APIs", () => {
    cy.visit("http://localhost:3000/interview");

    cy.window().then((win) => {
      expect(win.navigator.mediaDevices).to.exist;
      expect(win.navigator.mediaDevices.getUserMedia).to.be.a("function");
    });
  });
});