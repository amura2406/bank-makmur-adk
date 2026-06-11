import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ChatInterface from './ChatInterface';

describe('ChatInterface Component', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    // Spy and mock fetch to reject immediately to trigger mock response fallback by default
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('renders initial welcome state correctly and attempts session initialization', async () => {
    // Mock successful session initialization fetch
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'initial-session-id-777' }),
    } as Response);

    await act(async () => {
      render(<ChatInterface />);
    });
    
    // Check Header and Title
    expect(screen.getByText('Tanya Makmur')).toBeInTheDocument();
    expect(screen.getByText('Asisten Virtual')).toBeInTheDocument();
    
    // Check Welcome Message
    expect(screen.getByText(/Halo! Saya Tanya Makmur, asisten virtual Anda/i)).toBeInTheDocument();
    
    // Check Input and Send Button
    const input = screen.getByPlaceholderText('Tulis pesan...');
    expect(input).toBeInTheDocument();
    expect(input).not.toBeDisabled();
    
    const sendButton = screen.getByLabelText('Kirim');
    expect(sendButton).toBeInTheDocument();
    expect(sendButton).toBeDisabled(); // disabled when empty

    // Verify session initialization fetch was attempted
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('/sessions'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('allows user to type and enable send button', async () => {
    await act(async () => {
      render(<ChatInterface />);
    });
    
    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    const sendButton = screen.getByLabelText('Kirim');
    
    fireEvent.change(input, { target: { value: 'Halo' } });
    expect(input.value).toBe('Halo');
    expect(sendButton).not.toBeDisabled();
  });

  it('displays loading state and new placeholder when a message is sent', async () => {
    await act(async () => {
      render(<ChatInterface />);
    });
    
    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Berapa saldo saya?' } });
    
    const form = input.closest('form');
    expect(form).toBeInTheDocument();
    
    await act(async () => {
      fireEvent.submit(form!);
    });
    
    // User message should be displayed immediately
    expect(screen.getByText('Berapa saldo saya?')).toBeInTheDocument();
    
    // Input should be disabled
    expect(input).toBeDisabled();
    
    // Placeholder should show the loading message
    expect(screen.getByPlaceholderText('Looking up that information for you...')).toBeInTheDocument();
  });

  it('receives correct response for "saldo" keyword after timeout', async () => {
    await act(async () => {
      render(<ChatInterface />);
    });
    
    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'saldo' } });
    
    const form = input.closest('form')!;
    await act(async () => {
      fireEvent.submit(form);
    });
    
    // Verify loading state is active before advancing time
    expect(screen.getByPlaceholderText('Looking up that information for you...')).toBeInTheDocument();
    
    // Flush microtasks to allow the fetch rejection and subsequent catch block to run
    await act(async () => {
      await Promise.resolve();
    });
    
    // Advance timers by 1000ms
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    
    // Check response
    expect(screen.getByText(/Saldo akun Anda aman dan terjaga/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Tulis pesan...')).toBeInTheDocument();
  });

  it('receives correct response for "bunga" keyword after timeout', async () => {
    await act(async () => {
      render(<ChatInterface />);
    });
    
    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'bunga' } });
    
    const form = input.closest('form')!;
    await act(async () => {
      fireEvent.submit(form);
    });
    
    await act(async () => {
      await Promise.resolve();
    });
    
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    
    expect(screen.getByText(/Suku bunga tabungan Bank Makmur saat ini adalah 4.5%/i)).toBeInTheDocument();
  });

  it('receives correct response for "pinjaman" keyword after timeout', async () => {
    await act(async () => {
      render(<ChatInterface />);
    });
    
    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'pinjaman' } });
    
    const form = input.closest('form')!;
    await act(async () => {
      fireEvent.submit(form);
    });
    
    await act(async () => {
      await Promise.resolve();
    });
    
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    
    expect(screen.getByText(/Kami menawarkan berbagai produk pinjaman/i)).toBeInTheDocument();
  });

  it('receives default fallback response for general messages', async () => {
    await act(async () => {
      render(<ChatInterface />);
    });
    
    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Ada berita apa hari ini?' } });
    
    const form = input.closest('form')!;
    await act(async () => {
      fireEvent.submit(form);
    });
    
    await act(async () => {
      await Promise.resolve();
    });
    
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    
    expect(screen.getByText(/Terima kasih atas pertanyaan Anda/i)).toBeInTheDocument();
  });

  // Integration unit test: tests what happens when backend API responds successfully with SSE stream
  it('calls backend API and displays streaming response if online', async () => {
    // Set up a mock fetch implementation
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('/sessions')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ id: 'mock-session-id-123' }),
        } as Response);
      }
      if (urlStr.includes('/run_sse')) {
        const chunks = [
          'data: {"content":{"parts":[{"text":"Halo! "}]}}\n',
          'data: {"content":{"parts":[{"text":"Ini respon "}]}}\n',
          'data: {"content":{"parts":[{"text":"streaming."}]}}\n',
          'data: [DONE]\n'
        ];
        let chunkIndex = 0;
        const mockReader = {
          read: async () => {
            if (chunkIndex < chunks.length) {
              const val = new TextEncoder().encode(chunks[chunkIndex]);
              chunkIndex++;
              return { value: val, done: false };
            }
            return { value: undefined, done: true };
          },
          releaseLock: () => {},
        };
        return Promise.resolve({
          ok: true,
          body: {
            getReader: () => mockReader,
          },
        } as unknown as Response);
      }
      return Promise.reject(new Error('Unknown url'));
    });

    await act(async () => {
      render(<ChatInterface isTestMode={true} />);
    });

    // Verify mount session call occurred
    expect(localStorage.getItem('bank_makmur_session_id')).toBe('mock-session-id-123');

    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Halo' } });
    
    const form = input.closest('form')!;
    await act(async () => {
      fireEvent.submit(form);
    });
    
    // Flush microtasks to allow fetch resolution and processing of response
    await act(async () => {
      await Promise.resolve();
    });

    // Expect typing indicator to be gone once first chunk is processed
    expect(screen.queryByTestId('typing-indicator')).not.toBeInTheDocument();

    // Check complete streamed response
    expect(screen.getByText('Halo! Ini respon streaming.')).toBeInTheDocument();
  });

  it('resets session and initializes a new session when clicking back button', async () => {
    let sessionCallCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('/sessions')) {
        sessionCallCount++;
        return Promise.resolve({
          ok: true,
          json: async () => ({ id: `session-id-${sessionCallCount}` }),
        } as Response);
      }
      return Promise.reject(new Error('Unknown url'));
    });

    await act(async () => {
      render(<ChatInterface />);
    });

    expect(localStorage.getItem('bank_makmur_session_id')).toBe('session-id-1');

    const backButton = screen.getByLabelText('Back');
    await act(async () => {
      fireEvent.click(backButton);
    });

    expect(localStorage.getItem('bank_makmur_session_id')).toBe('session-id-2');
  });

  it('clears pending fallback timeouts when session is reset', async () => {
    await act(async () => {
      render(<ChatInterface />);
    });

    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'saldo' } });

    const form = input.closest('form')!;
    await act(async () => {
      fireEvent.submit(form);
    });

    // Flush microtasks to let the promise rejection handler run and trigger the setTimeout
    await act(async () => {
      await Promise.resolve();
    });

    // Reset the session immediately before timer runs
    const backButton = screen.getByLabelText('Back');
    await act(async () => {
      fireEvent.click(backButton);
    });

    // Advance timer by 1000ms
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // The agent fallback response should NOT be rendered since the timeout was cleared
    expect(screen.queryByText(/Saldo akun Anda aman dan terjaga/i)).not.toBeInTheDocument();
  });

  it('has proper accessibility attributes for chat input and typing indicator', async () => {
    await act(async () => {
      render(<ChatInterface />);
    });

    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    expect(input).toHaveAttribute('aria-label', 'Tulis pesan');

    // Trigger typing state by sending a message
    fireEvent.change(input, { target: { value: 'Berapa saldo saya?' } });
    const form = input.closest('form')!;
    await act(async () => {
      fireEvent.submit(form);
    });

    const typingIndicator = screen.getByTestId('typing-indicator');
    expect(typingIndicator).toBeInTheDocument();
    expect(typingIndicator).toHaveAttribute('aria-live', 'polite');
    expect(typingIndicator).toHaveAttribute('role', 'status');
  });

  it('correctly formats double asterisks as bold and single asterisks as italic', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const urlStr = String(url);
      if (urlStr.includes('/sessions')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ id: 'mock-session-id-formatting' }),
        } as Response);
      }
      if (urlStr.includes('/run_sse')) {
        const chunks = [
          'data: {"content":{"parts":[{"text":"Halo! Ini **respon** yang *sangat* keren."}]}}\n',
          'data: [DONE]\n'
        ];
        let chunkIndex = 0;
        const mockReader = {
          read: async () => {
            if (chunkIndex < chunks.length) {
              const val = new TextEncoder().encode(chunks[chunkIndex]);
              chunkIndex++;
              return { value: val, done: false };
            }
            return { value: undefined, done: true };
          },
          releaseLock: () => {},
        };
        return Promise.resolve({
          ok: true,
          body: {
            getReader: () => mockReader,
          },
        } as unknown as Response);
      }
      return Promise.reject(new Error('Unknown url'));
    });

    await act(async () => {
      render(<ChatInterface isTestMode={true} />);
    });

    const input = screen.getByPlaceholderText('Tulis pesan...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'test' } });
    
    const form = input.closest('form')!;
    await act(async () => {
      fireEvent.submit(form);
    });
    
    await act(async () => {
      await Promise.resolve();
    });

    // Check that "respon" is inside a strong/bold tag
    const strongElement = screen.getByText('respon');
    expect(strongElement.tagName).toBe('STRONG');
    expect(strongElement).toHaveClass('font-semibold');

    // Check that "sangat" is inside an em/italic tag
    const emElement = screen.getByText('sangat');
    expect(emElement.tagName).toBe('EM');
    expect(emElement).toHaveClass('italic');
  });
});

