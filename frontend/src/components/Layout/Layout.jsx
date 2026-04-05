import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import {
  LayoutDashboard, Activity, BarChart3, History, Cpu, LogOut, Heart,
  ChevronRight, Scale, Minimize2, TrendingUp, Wand2, FlaskConical, Zap
} from 'lucide-react'
import clsx from 'clsx'

const userNav = [
  { to: '/',              icon: LayoutDashboard, label: 'Dashboard',        exact: true },
  { to: '/predict',       icon: Activity,        label: 'Predict' },
  { to: '/performance',   icon: BarChart3,        label: 'Performance' },
  { to: '/analytics',     icon: TrendingUp,       label: 'Analytics' },
  { to: '/history',       icon: History,          label: 'History' },
  { to: '/fairness',      icon: Scale,            label: 'Fairness' },
  { to: '/minimal',       icon: Minimize2,        label: 'Minimal Features' },
  { to: '/counterfactual',icon: Wand2,            label: 'What-If Explorer' },
]
const adminNav = [
  { to: '/ab-testing', icon: FlaskConical, label: 'A/B Testing' },
  { to: '/automl',     icon: Zap,          label: 'AutoML Tuning' },
  { to: '/train',      icon: Cpu,          label: 'Train Models' },
]

function NavItem({ to, icon: Icon, label, exact }) {
  return (
    <NavLink to={to} end={exact}
      className={({ isActive }) => clsx(
        'flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150 group',
        isActive
          ? 'bg-brand-50 text-brand-700 shadow-sm'
          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
      )}>
      {({ isActive }) => (
        <>
          <Icon className={clsx('w-4 h-4 flex-shrink-0',
            isActive ? 'text-brand-600' : 'text-slate-400 group-hover:text-slate-600')} />
          <span className="flex-1 truncate">{label}</span>
          {isActive && <ChevronRight className="w-3 h-3 text-brand-400" />}
        </>
      )}
    </NavLink>
  )
}

export default function Layout() {
  const { user, logout, isAdmin } = useAuthStore()
  const navigate = useNavigate()
  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="w-60 bg-white border-r border-slate-200 flex flex-col fixed inset-y-0 z-30">
        {/* Logo */}
        <div className="px-5 py-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-sm">
              <Heart className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="font-bold text-slate-900 text-sm leading-tight">MedPredict</p>
              <p className="text-[10px] text-slate-400">v3.0 · 10 features</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          <p className="px-3 text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1">
            Navigation
          </p>
          {userNav.map(item => <NavItem key={item.to} {...item} />)}

          {isAdmin() && (
            <>
              <p className="px-3 text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1 mt-3">
                Admin
              </p>
              {adminNav.map(item => <NavItem key={item.to} {...item} />)}
            </>
          )}
        </nav>

        {/* User */}
        <div className="px-2 py-3 border-t border-slate-100">
          <div className="flex items-center gap-3 px-3 py-2 rounded-xl">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {user?.username?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">{user?.username}</p>
              <p className="text-xs text-slate-400 capitalize">{user?.role}</p>
            </div>
            <button onClick={handleLogout}
              className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
              title="Logout">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 ml-60 min-h-screen">
        <div className="max-w-7xl mx-auto px-6 py-8 animate-in">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
