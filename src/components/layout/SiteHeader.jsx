import NavTabs from "./NavTabs.jsx";

export default function SiteHeader({ active, subtitle, children }) {
  return (
    <header>
      <div className="wrap hd">
        <div className="brand">
          <div className="mark">★</div>
          <div>
            <h1>Thông tin thị trường</h1>
            <p>{subtitle}</p>
          </div>
        </div>
        <NavTabs active={active} />
        <div className="hd-right">{children}</div>
      </div>
    </header>
  );
}
