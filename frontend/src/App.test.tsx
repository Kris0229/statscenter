import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { App } from "./App";
import { AuthProvider } from "./auth/AuthContext";

afterEach(() => {
  localStorage.clear();
});

function renderApp(initialPath: string) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={[initialPath]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App", () => {
  it("redirects an unauthenticated visitor to the login page", () => {
    renderApp("/games");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("登入");
  });

  it("shows the login form fields", () => {
    renderApp("/login");
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("密碼")).toBeInTheDocument();
  });
});
