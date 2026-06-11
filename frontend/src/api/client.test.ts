import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getOrCreateUserId,
  getStoredSessionId,
  getOrCreateSessionId,
  clearSession,
  sendStreamingMessage,
  submitFeedback
} from './client';

describe('API Client library', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getOrCreateUserId', () => {
    it('generates a new user ID if none exists in localStorage', () => {
      const id = getOrCreateUserId();
      expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
      expect(localStorage.getItem('bank_makmur_user_id')).toBe(id);
    });

    it('returns the existing user ID from localStorage if available', () => {
      localStorage.setItem('bank_makmur_user_id', 'existing-user-123');
      const id = getOrCreateUserId();
      expect(id).toBe('existing-user-123');
    });

    it('falls back to in-memory store in private browsing mode (when localStorage throws)', () => {
      vi.spyOn(localStorage, 'getItem').mockImplementation(() => {
        throw new Error('localStorage is blocked');
      });
      vi.spyOn(localStorage, 'setItem').mockImplementation(() => {
        throw new Error('localStorage is blocked');
      });

      // Should generate a UUID and work without throwing
      const id1 = getOrCreateUserId();
      expect(id1).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);

      // Subsequent call should retrieve the same ID from the in-memory fallback store
      const id2 = getOrCreateUserId();
      expect(id2).toBe(id1);
    });
  });

  describe('getStoredSessionId', () => {
    it('returns null if no session ID is stored', () => {
      expect(getStoredSessionId()).toBeNull();
    });

    it('returns the stored session ID', () => {
      localStorage.setItem('bank_makmur_session_id', 'session-123');
      expect(getStoredSessionId()).toBe('session-123');
    });
  });

  describe('getOrCreateSessionId', () => {
    it('returns existing session ID if forceNew is false', async () => {
      localStorage.setItem('bank_makmur_session_id', 'session-123');
      const fetchSpy = vi.spyOn(globalThis, 'fetch');

      const sId = await getOrCreateSessionId('user-123', false);
      expect(sId).toBe('session-123');
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it('calls fetch to create a new session if none exists', async () => {
      const mockSessionId = 'new-session-456';
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: async () => ({ id: mockSessionId }),
      } as Response);

      const sId = await getOrCreateSessionId('user-123', false);
      expect(sId).toBe(mockSessionId);
      expect(localStorage.getItem('bank_makmur_session_id')).toBe(mockSessionId);
      expect(fetchSpy).toHaveBeenCalledTimes(1);
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/apps/app/users/user-123/sessions'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            state: { preferred_language: 'Indonesian', visit_count: 1 }
          })
        })
      );
    });

    it('calls fetch to create a new session if forceNew is true even if one exists', async () => {
      localStorage.setItem('bank_makmur_session_id', 'session-123');
      const mockSessionId = 'forced-session-789';
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: async () => ({ id: mockSessionId }),
      } as Response);

      const sId = await getOrCreateSessionId('user-123', true);
      expect(sId).toBe(mockSessionId);
      expect(localStorage.getItem('bank_makmur_session_id')).toBe(mockSessionId);
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    it('throws error if session creation response is not ok', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
      } as Response);

      await expect(getOrCreateSessionId('user-123')).rejects.toThrow(
        'Failed to create session on backend: Internal Server Error'
      );
    });

    it('throws error if session creation response is empty', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: async () => ({}),
      } as Response);

      await expect(getOrCreateSessionId('user-123')).rejects.toThrow(
        'Session creation response did not contain session ID'
      );
    });
  });

  describe('clearSession', () => {
    it('removes the session ID from localStorage', () => {
      localStorage.setItem('bank_makmur_session_id', 'session-123');
      clearSession();
      expect(localStorage.getItem('bank_makmur_session_id')).toBeNull();
    });
  });

  describe('sendStreamingMessage', () => {
    it('submits a message to run_sse and processes incoming stream chunks', async () => {
      const chunks = [
        'data: {"content":{"parts":[{"text":"Halo, "}]}}\n',
        'data: {"content":{"parts":[{"text":"ada "}]}}\n',
        'data: {"content":{"parts":[{"text":"yang "}]}}\n',
        'data: {"content":{"parts":[{"text":"bisa "}]}}\n',
        'data: {"content":{"parts":[{"text":"dibantu?"}]}}\n',
        'data: [DONE]\n'
      ];

      let chunkIndex = 0;
      const mockReader = {
        read: vi.fn().mockImplementation(async () => {
          if (chunkIndex < chunks.length) {
            const val = new TextEncoder().encode(chunks[chunkIndex]);
            chunkIndex++;
            return { value: val, done: false };
          }
          return { value: undefined, done: true };
        }),
        releaseLock: vi.fn(),
      };

      const mockBody = {
        getReader: () => mockReader,
      };

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        body: mockBody,
      } as unknown as Response);

      const collectedChunks: string[] = [];
      const onChunk = (text: string) => {
        collectedChunks.push(text);
      };

      await sendStreamingMessage('user-123', 'session-123', 'Halo', onChunk);

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/run_sse'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            app_name: 'app',
            user_id: 'user-123',
            session_id: 'session-123',
            new_message: {
              role: 'user',
              parts: [{ text: 'Halo' }],
            },
            streaming: true,
          })
        })
      );

      expect(collectedChunks).toEqual(['Halo, ', 'ada ', 'yang ', 'bisa ', 'dibantu?']);
      expect(mockReader.releaseLock).toHaveBeenCalled();
    });

    it('throws error if response is not ok', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        statusText: 'Bad Request',
      } as Response);

      await expect(
        sendStreamingMessage('user-123', 'session-123', 'Halo', () => {})
      ).rejects.toThrow('Failed to initiate stream: Bad Request');
    });

    it('throws error if response body is null', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        body: null,
      } as Response);

      await expect(
        sendStreamingMessage('user-123', 'session-123', 'Halo', () => {})
      ).rejects.toThrow('Response body is not readable');
    });
  });

  describe('submitFeedback', () => {
    it('sends feedback data to feedback endpoint', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
      } as Response);

      const feedbackData = {
        score: 5,
        user_id: 'user-123',
        session_id: 'session-123',
        text: 'Very helpful!'
      };

      await submitFeedback(feedbackData);

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/feedback'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(feedbackData)
        })
      );
    });

    it('throws error if feedback request fails', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        statusText: 'Unauthorized',
      } as Response);

      await expect(
        submitFeedback({
          score: 1,
          user_id: 'u',
          session_id: 's',
          text: 'bad'
        })
      ).rejects.toThrow('Failed to submit feedback: Unauthorized');
    });
  });
});
