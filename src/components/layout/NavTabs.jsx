export default function NavTabs({ active }) {
  return (
    <nav className="nav" aria-label="Điều hướng chính">
      <a href="/index.html" aria-current={active === "dashboard" ? "page" : undefined}>
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect x="1.6" y="1.6" width="5.2" height="5.2" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
          <rect x="9.2" y="1.6" width="5.2" height="5.2" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
          <rect x="1.6" y="9.2" width="5.2" height="5.2" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
          <rect x="9.2" y="9.2" width="5.2" height="5.2" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
        </svg>
        <span>Trong nước</span>
      </a>
      <a href="/the-gioi.html" aria-current={active === "world" ? "page" : undefined}>
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="6.3" stroke="currentColor" strokeWidth="1.4" />
          <path d="M1.7 8h12.6M8 1.7c1.7 1.8 2.6 4 2.6 6.3S9.7 12.5 8 14.3C6.3 12.5 5.4 10.3 5.4 8S6.3 3.5 8 1.7z" stroke="currentColor" strokeWidth="1.3" />
        </svg>
        <span>Thế giới</span>
      </a>
    </nav>
  );
}
