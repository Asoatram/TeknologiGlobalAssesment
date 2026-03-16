import { NavLink } from 'react-router-dom'
import './Header.css'

const appIconUrl = 'https://www.figma.com/api/mcp/asset/74e9fed0-140e-4929-8d22-a5ecaa4a92d5'

export function Header() {
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `header-nav-link${isActive ? ' is-active' : ''}`

  return (
    <header className="top-nav" data-node-id="1:993">
      <div className="top-nav__left" data-node-id="1:994">
        <div className="brand-group" data-node-id="1:995">
          <div className="brand-icon-wrap" data-node-id="1:996">
            <img src={appIconUrl} alt="Inventory icon" className="icon-20" data-node-id="1:997" />
          </div>
          <h1 className="brand-title" data-node-id="1:1000">
            Inventory System
          </h1>
        </div>
      </div>

      <div className="top-nav__right" data-node-id="1:1010">
        <nav className="header-nav" aria-label="Primary">
          <NavLink to="/inventory" className={navClass}>
            Inventory
          </NavLink>
          <NavLink to="/insight" className={navClass}>
            Insight
          </NavLink>
        </nav>
      </div>
    </header>
  )
}
