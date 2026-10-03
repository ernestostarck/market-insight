import { test, expect } from '@playwright/test';

test.describe('Market Insight ChileCompra - Flujo E2E Completo', () => {
  test('Flujo completo: Login -> Dashboard -> Licitaciones -> Detalle -> IA & Calidad', async ({ page }) => {
    // 1. Acceder a la página de login
    await page.goto('/login');
    await expect(page).toHaveTitle(/Market Insight/i);

    // 2. Iniciar sesión con credenciales demo
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    const passwordInput = page.locator('input[type="password"], input[name="password"]');
    const submitBtn = page.getByRole('button', { name: /iniciar sesión|acceder|ingresar/i });

    if (await emailInput.isVisible()) {
      await emailInput.fill('analista@marketinsight.cl');
      await passwordInput.fill('demo1234');
      await submitBtn.click();
    }

    // 3. Verificar aterrizaje en Dashboard
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.getByText(/resumen ejecutivo|dashboard|observatorio/i).first()).toBeVisible();

    // 4. Navegar a Licitaciones
    await page.goto('/licitaciones');
    await expect(page).toHaveURL(/.*licitaciones/);
    await expect(page.getByText(/explorador de licitaciones|licitaciones públicas/i).first()).toBeVisible();

    // 5. Navegar al detalle de la primera licitación
    const firstTenderLink = page.locator('table tbody tr a, table tbody tr button').first();
    if (await firstTenderLink.isVisible()) {
      await firstTenderLink.click();
      await expect(page).toHaveURL(/.*licitaciones\/\d+/);
      await expect(page.getByText(/información general|bases técnicas|adjudicación/i).first()).toBeVisible();
    }

    // 6. Navegar al Módulo de IA & Calidad de Datos (Subfases 7.26 - 7.28)
    await page.goto('/ai');
    await expect(page).toHaveURL(/.*ai/);
    await expect(page.getByText('Inteligencia Artificial & Calidad de Datos')).toBeVisible();

    // 7. Navegar entre las pestañas del módulo de IA
    const pendingTab = page.getByRole('button', { name: /cola de revisión humana/i });
    if (await pendingTab.isVisible()) {
      await pendingTab.click();
      await expect(page.getByText(/cola de prioridad human-in-the-loop/i)).toBeVisible();
    }

    const qualityTab = page.getByRole('button', { name: /salud del sistema & calidad etl/i });
    if (await qualityTab.isVisible()) {
      await qualityTab.click();
      await expect(page.getByText(/tasa de completitud de datos/i)).toBeVisible();
      await expect(page.getByText('97.8%')).toBeVisible();
    }
  });
});
