describe('Recruiter Dashboard', () => {

  it('opens dashboard', () => {
    cy.visit('http://localhost:3000')

    cy.contains('Overview').should('be.visible')
  })

  it('opens Candidates page', () => {
    cy.visit('http://localhost:3000')

    cy.contains('Candidates').click()

    cy.url().should('include', '/candidates')
    cy.contains('Candidate List').should('be.visible')
  })

  it('opens Sessions page', () => {
    cy.visit('http://localhost:3000')

    cy.contains('Sessions').click()

    cy.url().should('include', '/sessions')
    cy.contains('Sessions').should('be.visible')
  })

})

describe('Data Export', () => {
  const mockSessions = {
    sessions: [
      {
        session_id: 'session-1',
        candidate_id: 'candidate-1',
        status: 'completed',
        start_time: '2024-01-15T10:00:00',
        risk_score: 0.2
      },
      {
        session_id: 'session-2',
        candidate_id: 'candidate-2',
        status: 'completed',
        start_time: '2024-01-16T14:00:00',
        risk_score: 0.5
      }
    ]
  }

  const mockPdfBlob = new Blob(['%PDF-1.4 fake pdf content'], { type: 'application/pdf' })

  beforeEach(() => {
    // Stub the download mechanism
    cy.window().then((win) => {
      cy.stub(win.URL, 'createObjectURL').returns('blob:fake-url')
      cy.stub(win.URL, 'revokeObjectURL').as('revokeURL')
    })
  })

  describe('Sessions Page CSV Export', () => {
    it('exports CSV when clicking Export CSV button', () => {
      // Intercept API calls
      cy.intercept('GET', '**/active-sessions*', { sessions: [] }).as('activeSessions')
      cy.intercept('GET', '**/completed-sessions*limit=10000*', mockSessions).as('completedSessions')
      cy.intercept('GET', '**/failed-sessions*limit=10000*', { sessions: [] }).as('failedSessions')

      cy.visit('http://localhost:3000/sessions')
      
      // Wait for data to load
      cy.wait('@activeSessions')
      cy.wait('@completedSessions')
      cy.wait('@failedSessions')

      // Click Export CSV button
      cy.contains('button', 'Export CSV').click()

      // Verify createObjectURL was called (download triggered)
      cy.window().then((win) => {
        expect(win.URL.createObjectURL).to.have.been.called
      })

      // Verify success toast
      cy.contains('CSV exported successfully').should('be.visible')
    })

    it('shows error when no data available', () => {
      cy.intercept('GET', '**/active-sessions*', { sessions: [] }).as('activeSessions')
      cy.intercept('GET', '**/completed-sessions*', { sessions: [] }).as('completedSessions')
      cy.intercept('GET', '**/failed-sessions*', { sessions: [] }).as('failedSessions')

      cy.visit('http://localhost:3000/sessions')
      
      cy.wait('@activeSessions')
      cy.wait('@completedSessions')
      cy.wait('@failedSessions')

      cy.contains('button', 'Export CSV').click()

      cy.contains('No data to export').should('be.visible')
    })
  })

  describe('Candidates Page CSV Export', () => {
    it('exports CSV when clicking Export CSV button', () => {
      cy.intercept('GET', '**/completed-sessions*limit=10000*', mockSessions).as('completedSessions')
      cy.intercept('GET', '**/failed-sessions*limit=10000*', { sessions: [] }).as('failedSessions')

      cy.visit('http://localhost:3000/candidates')
      
      cy.wait('@completedSessions')
      cy.wait('@failedSessions')

      cy.contains('button', 'Export CSV').click()

      cy.window().then((win) => {
        expect(win.URL.createObjectURL).to.have.been.called
      })

      cy.contains('CSV exported successfully').should('be.visible')
    })
  })

  describe('Analytics Page CSV Export', () => {
    it('exports CSV when clicking Export button', () => {
      cy.intercept('GET', '**/completed-sessions*limit=10000*', mockSessions).as('completedSessions')
      cy.intercept('GET', '**/failed-sessions*limit=10000*', { sessions: [] }).as('failedSessions')

      cy.visit('http://localhost:3000/analytics')
      
      cy.wait('@completedSessions')
      cy.wait('@failedSessions')

      cy.contains('button', 'Export').click()

      cy.window().then((win) => {
        expect(win.URL.createObjectURL).to.have.been.called
      })
    })
  })

  describe('Session Detail PDF Export', () => {
    const mockSessionDetail = {
      session_id: 'session-1',
      candidate_id: 'candidate-1',
      status: 'completed',
      start_time: '2024-01-15T10:00:00',
      video_analysis: {
        facial_expressions: JSON.stringify({ happy: 0.8, neutral: 0.2 }),
        gaze_direction: 'forward',
        confidence_score: 0.85
      },
      audio_analysis: {
        sentiment: 'positive',
        clarity_score: 0.9,
        speaking_pace: 'normal',
        filler_word_count: 2
      },
      ai_feedback: {
        overall_feedback: 'Excellent performance'
      }
    }

    it('exports PDF successfully using backend', () => {
      cy.intercept('GET', '**/active-sessions*', mockSessions).as('activeSessions')
      cy.intercept('GET', '**/session-status/session-1', mockSessionDetail).as('sessionStatus')
      cy.intercept('GET', '**/sessions/session-1/report/pdf', {
        statusCode: 200,
        headers: { 'content-type': 'application/pdf' },
        body: mockPdfBlob
      }).as('pdfDownload')

      cy.visit('http://localhost:3000/sessions')
      cy.wait('@activeSessions')

      // Click on first session to open detail modal
      cy.contains('session-1').click()
      cy.wait('@sessionStatus')

      // Click Export PDF button
      cy.get('[aria-label="Export PDF"]').click()

      cy.wait('@pdfDownload')

      // Verify success toast for complex report
      cy.contains('Complex report generated').should('be.visible')
    })

    it('falls back to browser PDF when backend fails', () => {
      cy.intercept('GET', '**/active-sessions*', mockSessions).as('activeSessions')
      cy.intercept('GET', '**/session-status/session-1', mockSessionDetail).as('sessionStatus')
      cy.intercept('GET', '**/sessions/session-1/report/pdf', {
        statusCode: 500,
        body: { detail: 'PDF generation failed' }
      }).as('pdfDownloadFail')

      cy.visit('http://localhost:3000/sessions')
      cy.wait('@activeSessions')

      cy.contains('session-1').click()
      cy.wait('@sessionStatus')

      cy.get('[aria-label="Export PDF"]').click()

      cy.wait('@pdfDownloadFail')

      // Verify fallback toast for basic report
      cy.contains('Basic report generated').should('be.visible')
    })

    it('shows error when both backend and browser PDF fail', () => {
      cy.intercept('GET', '**/active-sessions*', mockSessions).as('activeSessions')
      cy.intercept('GET', '**/session-status/session-1', mockSessionDetail).as('sessionStatus')
      cy.intercept('GET', '**/sessions/session-1/report/pdf', {
        statusCode: 500,
        body: { detail: 'PDF generation failed' }
      }).as('pdfDownloadFail')

      // Mock jsPDF to throw error
      cy.visit('http://localhost:3000/sessions')
      cy.window().then((win) => {
        win.jsPDF = class {
          constructor() {
            throw new Error('jsPDF initialization failed')
          }
        }
      })

      cy.wait('@activeSessions')

      cy.contains('session-1').click()
      cy.wait('@sessionStatus')

      cy.get('[aria-label="Export PDF"]').click()

      cy.wait('@pdfDownloadFail')

      // Verify error toast
      cy.contains('Failed to export PDF').should('be.visible')
    })

    it('disables button while PDF is being generated', () => {
      cy.intercept('GET', '**/active-sessions*', mockSessions).as('activeSessions')
      cy.intercept('GET', '**/session-status/session-1', mockSessionDetail).as('sessionStatus')
      cy.intercept('GET', '**/sessions/session-1/report/pdf', {
        statusCode: 200,
        headers: { 'content-type': 'application/pdf' },
        body: mockPdfBlob,
        delay: 1000 // Delay to test loading state
      }).as('pdfDownload')

      cy.visit('http://localhost:3000/sessions')
      cy.wait('@activeSessions')

      cy.contains('session-1').click()
      cy.wait('@sessionStatus')

      cy.get('[aria-label="Export PDF"]').click()

      // Button should be disabled during export
      cy.get('[aria-label="Export PDF"]').should('be.disabled')

      cy.wait('@pdfDownload')

      // Button should be enabled after export
      cy.get('[aria-label="Export PDF"]').should('not.be.disabled')
    })
  })
})

describe('Authentication and Interview Features', () => {
  it('stores JWT/API token and uses it for authenticated requests', () => {
    const token = 'test-jwt-token'

    cy.visit('http://localhost:3000', {
      onBeforeLoad(win) {
        win.localStorage.setItem('api_token', token)
      },
    })

    cy.window().then((win) => {
      expect(win.localStorage.getItem('api_token')).to.equal(token)
    })

    cy.intercept('GET', '**/system-health', (req) => {
      expect(req.headers.authorization).to.equal(`Bearer ${token}`)
    }).as('authenticatedRequest')

    cy.reload()

    cy.wait('@authenticatedRequest')
  })
  it('starts an interview from the interview page', () => {
    const token = 'test-jwt-token'
    const candidateId = 'cand-1234'
    const sessionId = 'session-test-123'

    const mockStream = new MediaStream()

    cy.intercept('POST', '**/start-interview', (req) => {
      expect(req.headers.authorization).to.equal(`Bearer ${token}`)

      expect(req.body).to.deep.equal({
        candidate_id: candidateId,
        priority: 'high',
      })

      req.reply({
        statusCode: 200,
        body: {
          session_id: sessionId,
          status: 'QUEUED',
          created_at: '2026-08-09T12:00:00Z',
          candidate_id: candidateId,
          risk_score: null,
          estimated_wait_time: 0,
        },
      })
    }).as('startInterview')

    cy.visit('http://localhost:3000/interview', {
      onBeforeLoad(win) {
        win.localStorage.setItem('api_token', token)

        const getUserMedia = cy.stub().resolves(mockStream)

        Object.defineProperty(win.navigator, 'mediaDevices', {
          configurable: true,
          value: {
            getUserMedia,
          },
        })

        class MockAudioContext {
          createMediaStreamSource() {
            return {
              connect() {},
            }
          }

          createAnalyser() {
            return {
              fftSize: 64,
              frequencyBinCount: 32,
              getByteFrequencyData() {},
            }
          }

          close() {
            return Promise.resolve()
          }
        }

        win.AudioContext = MockAudioContext
        win.webkitAudioContext = MockAudioContext
      },
    })

    cy.contains('Live Interview')
      .should('be.visible')

    cy.get('input[placeholder="cand-1234"]')
      .should('be.visible')
      .type(candidateId)

    cy.contains('button', 'Start Interview')
      .should('be.enabled')
      .click()

    cy.wait('@startInterview')

    cy.contains('LIVE')
      .should('be.visible')

    cy.contains(sessionId)
      .should('be.visible')

    cy.contains('section', 'Session Info')
      .should('contain', candidateId)
      .and('contain', 'Live')
  })
  it('views the sessions list and opens a session', () => {
  const token = 'test-jwt-token'
  const sessionId = 'session-test-123'
  const candidateId = 'cand-1234'

  cy.intercept('GET', '**/active-sessions*', {
    statusCode: 200,
    body: {
      sessions: [
        {
          session_id: sessionId,
          candidate_id: candidateId,
          status: 'QUEUED',
          risk_score: 0.25,
          assigned_node: 'worker-1',
          created_at: '2026-08-09T11:59:00Z',
          updated_at: '2026-08-09T12:00:00Z'
        }
      ]
    }
  }).as('activeSessions')

  cy.intercept('GET', `**/session-status/${sessionId}`, {
    statusCode: 200,
    body: {
      session_id: sessionId,
      candidate_id: candidateId,
      status: 'QUEUED',
      risk_score: 0.25,
      assigned_node: 'worker-1',
      created_at: '2026-08-09T11:59:00Z',
      updated_at: '2026-08-09T12:00:00Z'
    }
  }).as('sessionDetail')

  cy.intercept('GET', `**/moments/${sessionId}`, {
    statusCode: 200,
    body: {
      moments: []
    }
  }).as('sessionMoments')

  cy.visit('http://localhost:3000/sessions', {
    onBeforeLoad(win) {
      win.localStorage.setItem('api_token', token)
    }
  })

  cy.wait('@activeSessions')

  cy.contains('h1', 'Sessions')
    .should('be.visible')

  cy.get(`[data-testid="session-row-${sessionId}"]`)
    .should('be.visible')
    .and('contain', sessionId)

  cy.get(`[data-testid="session-row-${sessionId}"]`)
    .click()

  cy.get('[data-testid="session-dialog"]')
    .should('be.visible')

  cy.wait('@sessionDetail')

  cy.get('[data-testid="session-dialog"]')
    .should('contain', sessionId)
    .and('contain', 'QUEUED')
    .and('contain', 'worker-1')
})
  it('shows validation error for invalid candidate email', () => {
  cy.visit('http://localhost:3000/candidates');

  cy.get('#candidate-name')
    .type('Jane Doe');

  cy.get('#candidate-email')
    .type('invalid-email');

  cy.get('#candidate-email')
    .then(($input) => {
      expect($input[0].checkValidity()).to.equal(false);
    });

  cy.get('#candidate-email')
    .should('have.attr', 'type', 'email');
});
it("registers a candidate successfully with valid data", () => {
    const candidate = {
      candidate_id: "cand-test-001",
      name: "Jane Doe",
      email: "jane.doe@example.com",
      resume_text: "Experienced software engineer",
      skills: ["Java", "Python", "React"],
    };

    cy.intercept("POST", "**/candidates", (req) => {
      expect(req.body).to.deep.equal({
        name: candidate.name,
        email: candidate.email,
        resume_text: candidate.resume_text,
        skills: candidate.skills,
      });

      req.reply({
        statusCode: 201,
        body: candidate,
      });
    }).as("createCandidate");

    cy.visit("http://localhost:3000/candidates");

    cy.get("#candidate-name")
      .should("be.visible")
      .type(candidate.name);

    cy.get("#candidate-email")
      .should("be.visible")
      .type(candidate.email);

    cy.get("#candidate-resume")
      .should("be.visible")
      .type(candidate.resume_text);

    cy.get("#candidate-skills")
      .should("be.visible")
      .type("Java, Python, React");

    cy.contains("button", "Register Candidate")
      .should("be.enabled")
      .click();

    cy.wait("@createCandidate");

    cy.get('[role="status"]')
      .should("be.visible")
      .and(
        "contain",
        "Candidate cand-test-001 registered successfully."
      );

    cy.get("#candidate-name")
      .should("have.value", "");

    cy.get("#candidate-email")
      .should("have.value", "");

    cy.get("#candidate-resume")
      .should("have.value", "");

    cy.get("#candidate-skills")
      .should("have.value", "");
  });
})
