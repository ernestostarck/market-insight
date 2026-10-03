import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { ChatView } from '../features/ai/chat/ChatView';
import { ControlledMarkdown } from '../features/ai/chat/ControlledMarkdown';
import { apiClient } from '../api/client';

// Mock API client
vi.mock('../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  getToken: vi.fn(() => 'test-jwt-token'),
}));

describe('MercadoInsight React Chat Feature (Subfase 9.28)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/chat/conversations') {
        return Promise.resolve({
          data: [
            {
              id: 'conv-123',
              title: 'Licitaciones de Ambulancias',
              status: 'active',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
        });
      }
      if (url === '/chat/conversations/conv-123') {
        return Promise.resolve({
          data: {
            conversation: {
              id: 'conv-123',
              title: 'Licitaciones de Ambulancias',
              status: 'active',
            },
            messages: [
              {
                id: 'msg-1',
                conversation_id: 'conv-123',
                role: 'user',
                content: '¿Qué hospitales compraron ambulancias?',
                created_at: new Date().toISOString(),
              },
              {
                id: 'msg-2',
                conversation_id: 'conv-123',
                role: 'assistant',
                content: 'Durante 2024, el **Hospital San Juan** adquirió 3 ambulancias.',
                created_at: new Date().toISOString(),
              },
            ],
          },
        });
      }
      return Promise.reject(new Error(`Unhandled GET url: ${url}`));
    });
  });

  it('renders ChatView with conversation list and message history', async () => {
    render(<ChatView />);

    await screen.findAllByText('Licitaciones de Ambulancias');
    expect(await screen.findByText('¿Qué hospitales compraron ambulancias?')).toBeInTheDocument();
    expect(await screen.findByText(/Durante 2024, el/i)).toBeInTheDocument();
  });

  it('renders ControlledMarkdown tables and code blocks correctly', () => {
    const markdownWithTable = `
Resultados de la consulta:
| Organismo | Monto CLP | Licitaciones |
|---|---|---|
| Cenabast | $1.200.000.000 | 45 |
| Hospital Barros Luco | $450.000.000 | 12 |

\`\`\`sql
SELECT * FROM licitaciones;
\`\`\`
    `;

    render(<ControlledMarkdown content={markdownWithTable} />);

    expect(screen.getByText('Cenabast')).toBeInTheDocument();
    expect(screen.getByText('$1.200.000.000')).toBeInTheDocument();
    expect(screen.getByText('Hospital Barros Luco')).toBeInTheDocument();
    expect(screen.getByText('SELECT * FROM licitaciones;')).toBeInTheDocument();
  });

  it('allows clicking thumbs up feedback button', async () => {
    (apiClient.post as any).mockResolvedValue({ data: { success: true } });

    render(<ChatView />);
    await screen.findAllByText('Licitaciones de Ambulancias');

    const thumbsUpButtons = screen.getAllByTitle('Respuesta precisa');
    expect(thumbsUpButtons.length).toBeGreaterThan(0);

    fireEvent.click(thumbsUpButtons[0]);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/chat/messages/msg-2/feedback',
        expect.objectContaining({
          message_id: 'msg-2',
          rating: 1,
        })
      );
    });
  });

  it('creates a new conversation when clicking Nueva Conversación button', async () => {
    (apiClient.post as any).mockResolvedValue({
      data: {
        id: 'conv-new-999',
        title: 'Nueva consulta',
        status: 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });

    render(<ChatView />);
    await screen.findAllByText('Licitaciones de Ambulancias');

    const newBtn = screen.getByText('Nueva Conversación');
    fireEvent.click(newBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/chat/conversations', {
        title: 'Nueva consulta',
      });
    });
  });
});
