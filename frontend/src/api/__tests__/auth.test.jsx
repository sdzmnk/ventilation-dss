
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "../auth.jsx";

vi.mock("../client.js", () => ({
  api: {
    post: vi.fn(),
  },
}));

import { api } from "../client.js";

const FAKE_USER = { id: 1, username: "alice", email: "alice@test.com", role: "operator" };
const FAKE_TOKENS = {
  access_token: "access.tok",
  refresh_token: "refresh.tok",
  user: FAKE_USER,
};

function TestConsumer() {
  const { user, ready, logout } = useAuth();
  return (
    <div>
      <span data-testid="ready">{String(ready)}</span>
      <span data-testid="user">{user ? user.username : "null"}</span>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

function LoginConsumer() {
  const { login, user } = useAuth();
  return (
    <div>
      <span data-testid="user">{user ? user.username : "null"}</span>
      <button onClick={() => login("alice", "pass")}>Login</button>
    </div>
  );
}

function RegisterConsumer() {
  const { register, user } = useAuth();
  return (
    <div>
      <span data-testid="user">{user ? user.username : "null"}</span>
      <button onClick={() => register({ username: "bob", email: "b@b.com", password: "p" })}>Register</button>
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

afterEach(() => {
  localStorage.clear();
});

describe("AuthProvider — initial state", () => {
  it("is ready after mount", async () => {
    render(<AuthProvider><TestConsumer /></AuthProvider>);
    await waitFor(() => {
      expect(screen.getByTestId("ready").textContent).toBe("true");
    });
  });

  it("user is null when localStorage is empty", async () => {
    render(<AuthProvider><TestConsumer /></AuthProvider>);
    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("null");
    });
  });

  it("restores user from localStorage if token present", async () => {
    localStorage.setItem("vdss.token", "tok");
    localStorage.setItem("vdss.user", JSON.stringify(FAKE_USER));

    render(<AuthProvider><TestConsumer /></AuthProvider>);
    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("alice");
    });
  });

  it("does not restore user if token missing even if user cached", async () => {
    localStorage.setItem("vdss.user", JSON.stringify(FAKE_USER));

    render(<AuthProvider><TestConsumer /></AuthProvider>);
    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("null");
    });
  });

  it("ignores malformed JSON in vdss.user gracefully", async () => {
    localStorage.setItem("vdss.token", "tok");
    localStorage.setItem("vdss.user", "not-json{{{");

    render(<AuthProvider><TestConsumer /></AuthProvider>);
    await waitFor(() => {
      expect(screen.getByTestId("ready").textContent).toBe("true");
    });
  });
});

describe("AuthProvider — login()", () => {
  it("calls api.post with correct path and credentials", async () => {
    api.post.mockResolvedValueOnce({ data: FAKE_TOKENS });

    render(<AuthProvider><LoginConsumer /></AuthProvider>);
    await act(async () => {
      screen.getByText("Login").click();
    });

    expect(api.post).toHaveBeenCalledWith("/auth/login", { username: "alice", password: "pass" });
  });

  it("sets user in context after login", async () => {
    api.post.mockResolvedValueOnce({ data: FAKE_TOKENS });

    render(<AuthProvider><LoginConsumer /></AuthProvider>);
    await act(async () => {
      screen.getByText("Login").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("alice");
    });
  });

  it("persists tokens to localStorage after login", async () => {
    api.post.mockResolvedValueOnce({ data: FAKE_TOKENS });

    render(<AuthProvider><LoginConsumer /></AuthProvider>);
    await act(async () => {
      screen.getByText("Login").click();
    });

    await waitFor(() => {
      expect(localStorage.getItem("vdss.token")).toBe("access.tok");
      expect(localStorage.getItem("vdss.refresh")).toBe("refresh.tok");
      expect(JSON.parse(localStorage.getItem("vdss.user"))).toMatchObject({ username: "alice" });
    });
  });
});

describe("AuthProvider — register()", () => {
  it("calls api.post with /auth/register", async () => {
    api.post.mockResolvedValueOnce({ data: FAKE_TOKENS });

    render(<AuthProvider><RegisterConsumer /></AuthProvider>);
    await act(async () => {
      screen.getByText("Register").click();
    });

    expect(api.post).toHaveBeenCalledWith(
      "/auth/register",
      { username: "bob", email: "b@b.com", password: "p" }
    );
  });

  it("sets user in context after registration", async () => {
    const bobTokens = { ...FAKE_TOKENS, user: { ...FAKE_USER, username: "bob" } };
    api.post.mockResolvedValueOnce({ data: bobTokens });

    render(<AuthProvider><RegisterConsumer /></AuthProvider>);
    await act(async () => {
      screen.getByText("Register").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("bob");
    });
  });
});

describe("AuthProvider — logout()", () => {
  it("clears localStorage on logout", async () => {
    localStorage.setItem("vdss.token", "tok");
    localStorage.setItem("vdss.refresh", "ref");
    localStorage.setItem("vdss.user", JSON.stringify(FAKE_USER));

    render(<AuthProvider><TestConsumer /></AuthProvider>);
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("alice"));

    await act(async () => {
      screen.getByText("Logout").click();
    });

    expect(localStorage.getItem("vdss.token")).toBeNull();
    expect(localStorage.getItem("vdss.refresh")).toBeNull();
    expect(localStorage.getItem("vdss.user")).toBeNull();
  });

  it("sets user to null after logout", async () => {
    localStorage.setItem("vdss.token", "tok");
    localStorage.setItem("vdss.user", JSON.stringify(FAKE_USER));

    render(<AuthProvider><TestConsumer /></AuthProvider>);
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("alice"));

    await act(async () => {
      screen.getByText("Logout").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("null");
    });
  });
});
