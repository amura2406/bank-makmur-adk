export interface SSEEvent {
  content?: {
    parts?: Array<{
      text?: string;
    }>;
  };
}

export interface FeedbackData {
  score: number;
  user_id: string;
  session_id: string;
  text: string;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const inMemoryStore: Record<string, string> = {};

function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch (e) {
    return inMemoryStore[key] || null;
  }
}

function safeSetItem(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch (e) {
    inMemoryStore[key] = value;
  }
}

function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch (e) {
    delete inMemoryStore[key];
  }
}

/**
 * Gets the current user ID from local storage, or generates a new one if it doesn't exist.
 */
export function getOrCreateUserId(): string {
  let userId = safeGetItem('bank_makmur_user_id');
  if (!userId) {
    userId = crypto.randomUUID();
    safeSetItem('bank_makmur_user_id', userId);
  }
  return userId;
}

/**
 * Gets the current session ID from local storage.
 */
export function getStoredSessionId(): string | null {
  return safeGetItem('bank_makmur_session_id');
}

/**
 * Creates a new session on the backend and saves the session ID to local storage.
 * If a session already exists in local storage, it returns it unless forceNew is true.
 */
export async function getOrCreateSessionId(userId: string, forceNew = false): Promise<string> {
  let sessionId = safeGetItem('bank_makmur_session_id');
  if (sessionId && !forceNew) {
    return sessionId;
  }

  const response = await fetch(`${API_BASE}/apps/app/users/${userId}/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      state: { preferred_language: 'Indonesian', visit_count: 1 }
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to create session on backend: ${response.statusText}`);
  }

  const data = await response.json();
  sessionId = data.id;
  if (!sessionId) {
    throw new Error('Session creation response did not contain session ID');
  }

  safeSetItem('bank_makmur_session_id', sessionId);
  return sessionId;
}

/**
 * Clears the stored session ID from local storage, forcing a new session on the next call.
 */
export function clearSession(): void {
  safeRemoveItem('bank_makmur_session_id');
}

/**
 * Sends a message to the agent and parses the returned SSE stream chunk-by-chunk.
 * Calls the onChunk callback for every text segment received.
 */
export async function sendStreamingMessage(
  userId: string,
  sessionId: string,
  messageText: string,
  onChunk: (text: string) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/run_sse`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      app_name: 'app',
      user_id: userId,
      session_id: sessionId,
      new_message: {
        role: 'user',
        parts: [{ text: messageText }],
      },
      streaming: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to initiate stream: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('Response body is not readable');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let done = false;
  let buffer = '';

  const processLine = (line: string) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    
    if (trimmed.startsWith('data: ')) {
      const dataStr = trimmed.slice(6);
      if (dataStr === '[DONE]') return;
      try {
        const event: SSEEvent = JSON.parse(dataStr);
        const parts = event.content?.parts;
        if (parts && Array.isArray(parts)) {
          for (const part of parts) {
            if (part.text) {
              onChunk(part.text);
            }
          }
        }
      } catch (err) {
        // Secure logging to prevent printing raw chunks to console.log/console.warn
        // console.warn('Failed to parse SSE line JSON:', dataStr, err);
      }
    }
  };

  try {
    while (!done) {
      const { value, done: doneReading } = await reader.read();
      done = doneReading;
      if (value) {
        buffer += decoder.decode(value, { stream: !done });
        const lines = buffer.split('\n');
        // Save the last element because it might be incomplete
        buffer = lines.pop() || '';
        for (const line of lines) {
          processLine(line);
        }
      }
    }
    // Flush any remaining content in the buffer
    if (buffer) {
      processLine(buffer);
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Submits user feedback for the session.
 */
export async function submitFeedback(feedback: FeedbackData): Promise<void> {
  const response = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(feedback),
  });

  if (!response.ok) {
    throw new Error(`Failed to submit feedback: ${response.statusText}`);
  }
}
