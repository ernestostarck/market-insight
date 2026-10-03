import { describe, expect, it, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { NotificationsMenu } from '@/features/notifications';

function renderMenu() {
  return render(
    <MemoryRouter>
      <NotificationsMenu />
    </MemoryRouter>,
  );
}

// Radix's dropdown trigger opens on pointerdown, which plain fireEvent.click does not
// dispatch in jsdom — userEvent.click does.
async function openMenu() {
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: /notificaciones del sistema/i }));
  await waitFor(() => expect(screen.getByText('Notificaciones')).toBeInTheDocument());
}

describe('NotificationsMenu', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('shows an unread badge count and opens the panel with seeded notifications', async () => {
    renderMenu();

    expect(screen.getByText('2')).toBeInTheDocument(); // 2 unread out of 3 seeded

    await openMenu();
    expect(screen.getByText('3 licitaciones con cambios hoy')).toBeInTheDocument();
    expect(screen.getByText('Nueva adjudicación relevante')).toBeInTheDocument();
    expect(screen.getByText('Calidad de datos en revisión')).toBeInTheDocument();
  });

  it('deletes a single notification and it does not come back after remount', async () => {
    const first = renderMenu();
    await openMenu();

    fireEvent.click(screen.getAllByLabelText('Eliminar notificación')[0]);
    await waitFor(() =>
      expect(screen.queryByText('3 licitaciones con cambios hoy')).not.toBeInTheDocument(),
    );
    first.unmount();

    // Persisted: a fresh mount must not resurrect the deleted notification.
    renderMenu();
    await openMenu();
    expect(screen.queryAllByText('3 licitaciones con cambios hoy')).toHaveLength(0);
  });

  it('"Limpiar" removes every notification and shows the empty state', async () => {
    renderMenu();
    await openMenu();

    fireEvent.click(screen.getByRole('button', { name: /limpiar/i }));
    await waitFor(() => expect(screen.getByText('No tienes notificaciones')).toBeInTheDocument());
    expect(screen.queryByText(/notificaciones sin leer/i)).not.toBeInTheDocument();
  });

  it('"Marcar leídas" clears the unread badge without deleting anything', async () => {
    renderMenu();
    await openMenu();

    fireEvent.click(screen.getByRole('button', { name: /marcar leídas/i }));
    await waitFor(() => expect(screen.queryByText('2')).not.toBeInTheDocument());
    expect(screen.getByText('3 licitaciones con cambios hoy')).toBeInTheDocument();
  });
});
