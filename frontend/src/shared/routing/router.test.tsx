import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  Link,
  MemoryRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
  useSearchParams,
} from "./router";

describe("ForgeML router", () => {
  it("matches memory routes and navigates through links", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Link to="/projects">Projects</Link>
        <Routes>
          <Route path="/" element={<h1>Dashboard</h1>} />
          <Route path="/projects" element={<h1>Projects</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Projects" }));

    expect(
      screen.getByRole("heading", { name: "Projects" }),
    ).toBeInTheDocument();
  });

  it("resolves search params and redirects with Navigate", () => {
    render(
      <MemoryRouter initialEntries={["/login?redirect=/settings"]}>
        <Routes>
          <Route path="/login" element={<RedirectReader />} />
          <Route path="/settings" element={<h1>Settings</h1>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Settings" }),
    ).toBeInTheDocument();
  });

  it("applies active state for navigation links", () => {
    render(
      <MemoryRouter initialEntries={["/monitoring"]}>
        <NavLink
          to="/monitoring"
          className={({ isActive }) => (isActive ? "active" : "inactive")}
        >
          Monitoring
        </NavLink>
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Monitoring" })).toHaveClass(
      "active",
    );
  });
});

function RedirectReader() {
  const [searchParams] = useSearchParams();
  return <Navigate to={searchParams.get("redirect") ?? "/"} replace />;
}
