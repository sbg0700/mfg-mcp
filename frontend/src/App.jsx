import Breadcrumb from './components/Breadcrumb.jsx'
import ModelDropdown from './components/ModelDropdown.jsx'

export default function App({ children }) {
  return (
    <div className="app">
      <header className="topbar">
        <Breadcrumb />
        <ModelDropdown />
      </header>
      <main className="page">{children}</main>
    </div>
  )
}
