/* eslint-disable react-refresh/only-export-components */
import {
  Children,
  type AnchorHTMLAttributes,
  type ReactElement,
  type ReactNode,
  createContext,
  isValidElement,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type NavigateOptions = {
  replace?: boolean;
};

type RouterContextValue = {
  location: string;
  navigate: (to: string, options?: NavigateOptions) => void;
};

type RouteProps = {
  path: string;
  element: ReactNode;
};

type LinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  to: string;
};

type NavLinkProps = Omit<LinkProps, "className"> & {
  className?: string | ((state: { isActive: boolean }) => string);
};

const RouterContext = createContext<RouterContextValue | null>(null);

export function BrowserRouter({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState(getBrowserLocation);

  useEffect(() => {
    const handlePopState = () => setLocation(getBrowserLocation());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const value = useMemo<RouterContextValue>(
    () => ({
      location,
      navigate: (to, options) => {
        const nextLocation = normalizeLocation(to);
        if (options?.replace) {
          window.history.replaceState(null, "", nextLocation);
        } else {
          window.history.pushState(null, "", nextLocation);
        }
        setLocation(nextLocation);
      },
    }),
    [location],
  );

  return (
    <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
  );
}

export function MemoryRouter({
  children,
  initialEntries = ["/"],
}: {
  children: ReactNode;
  initialEntries?: string[];
}) {
  const [location, setLocation] = useState(() =>
    normalizeLocation(initialEntries[0] ?? "/"),
  );

  const value = useMemo<RouterContextValue>(
    () => ({
      location,
      navigate: (to) => setLocation(normalizeLocation(to)),
    }),
    [location],
  );

  return (
    <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
  );
}

export function Routes({ children }: { children: ReactNode }) {
  const { location } = useRouterContext();
  const pathname = locationPathname(location);
  const routes = Children.toArray(children).filter(isRouteElement);
  const fallback = routes.find((route) => route.props.path === "*");
  const match =
    routes.find((route) => route.props.path === pathname) ?? fallback;
  return match ? <>{match.props.element}</> : null;
}

export function Route(props: RouteProps) {
  void props;
  return null;
}

export function Navigate({
  to,
  replace = false,
}: {
  to: string;
  replace?: boolean;
}) {
  const navigate = useNavigate();
  useEffect(() => {
    navigate(to, { replace });
  }, [navigate, replace, to]);
  return null;
}

export function Link({ to, onClick, children, ...props }: LinkProps) {
  const navigate = useNavigate();
  return (
    <a
      {...props}
      href={to}
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented || shouldLetBrowserHandleClick(event)) {
          return;
        }
        event.preventDefault();
        navigate(to);
      }}
    >
      {children}
    </a>
  );
}

export function NavLink({ to, className, ...props }: NavLinkProps) {
  const { location } = useRouterContext();
  const isActive = locationPathname(location) === locationPathname(to);
  const resolvedClassName =
    typeof className === "function" ? className({ isActive }) : className;
  return <Link {...props} to={to} className={resolvedClassName} />;
}

export function useNavigate() {
  return useRouterContext().navigate;
}

export function useSearchParams(): [URLSearchParams] {
  const { location } = useRouterContext();
  return useMemo(
    () => [new URLSearchParams(locationSearch(location))],
    [location],
  );
}

function useRouterContext(): RouterContextValue {
  const context = useContext(RouterContext);
  if (context === null) {
    throw new Error("ForgeML router hooks must be used inside a router.");
  }
  return context;
}

function isRouteElement(value: ReactNode): value is ReactElement<RouteProps> {
  return isValidElement<RouteProps>(value) && value.type === Route;
}

function getBrowserLocation(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function normalizeLocation(value: string): string {
  return value.startsWith("/") ? value : `/${value}`;
}

function locationPathname(value: string): string {
  return normalizeLocation(value).split(/[?#]/, 1)[0] || "/";
}

function locationSearch(value: string): string {
  const queryStart = value.indexOf("?");
  if (queryStart === -1) {
    return "";
  }
  const hashStart = value.indexOf("#", queryStart);
  return value.slice(queryStart + 1, hashStart === -1 ? undefined : hashStart);
}

function shouldLetBrowserHandleClick(
  event: React.MouseEvent<HTMLAnchorElement>,
): boolean {
  return (
    event.button !== 0 ||
    event.metaKey ||
    event.altKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.currentTarget.target === "_blank"
  );
}
