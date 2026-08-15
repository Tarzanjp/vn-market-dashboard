export default function NavTabs({ active }) {
  return (
    <nav className="nav" aria-label="Điều hướng chính">
      <a href="buc-tranh-thi-truong.html" aria-current={active === "regime" ? "page" : undefined}>
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="6.3" stroke="currentColor" strokeWidth="1.4" />
          <circle cx="8" cy="8" r="2.4" stroke="currentColor" strokeWidth="1.4" />
          <circle cx="8" cy="8" r="0.9" fill="currentColor" />
        </svg>
        <span>Bức tranh</span>
      </a>
      <a href="index.html" aria-current={active === "dashboard" ? "page" : undefined}>
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect x="1.6" y="1.6" width="5.2" height="5.2" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
          <rect x="9.2" y="1.6" width="5.2" height="5.2" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
          <rect x="1.6" y="9.2" width="5.2" height="5.2" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
          <rect x="9.2" y="9.2" width="5.2" height="5.2" rx="1.4" stroke="currentColor" strokeWidth="1.4" />
        </svg>
        <span>Trong nước</span>
      </a>
      <a href="the-gioi.html" aria-current={active === "world" ? "page" : undefined}>
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="8" cy="8" r="6.3" stroke="currentColor" strokeWidth="1.4" />
          <path d="M1.7 8h12.6M8 1.7c1.7 1.8 2.6 4 2.6 6.3S9.7 12.5 8 14.3C6.3 12.5 5.4 10.3 5.4 8S6.3 3.5 8 1.7z" stroke="currentColor" strokeWidth="1.3" />
        </svg>
        <span>Thế giới</span>
      </a>
      <a href="lich-su.html" aria-current={active === "history" ? "page" : undefined}>
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M8 1.7a6.3 6.3 0 1 1-6.3 6.3M8 1.7v4.6l3.6 2.1M1.7 3.4v3.4h3.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>Lịch sử</span>
      </a>
      <a href="dong-tien-nganh.html" aria-current={active === "sectorFlows" ? "page" : undefined}>
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M13.6 8A5.6 5.6 0 1 1 11.8 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          <path d="M11.6 1.6v2.7h2.7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>Dòng tiền ngành</span>
      </a>
      <a href="dong-tien-cashout.html" aria-current={active === "cashout" ? "page" : undefined}>
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M8 1.8c2.6 3.1 4.3 5.5 4.3 7.7a4.3 4.3 0 1 1-8.6 0c0-2.2 1.7-4.6 4.3-7.7z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
        </svg>
        <span>Cashout</span>
      </a>
    </nav>
  );
}
