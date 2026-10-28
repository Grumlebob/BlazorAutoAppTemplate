import { useEffect, useRef } from "react";
import { useLocation } from "react-router";

export function RouteFocusManager() {
  const { pathname } = useLocation();
  const previousPathname = useRef(pathname);

  useEffect(() => {
    if (previousPathname.current === pathname) {
      return;
    }

    previousPathname.current = pathname;
    const main = document.getElementById("main-content");
    main?.focus({ preventScroll: true });
  }, [pathname]);

  return null;
}
