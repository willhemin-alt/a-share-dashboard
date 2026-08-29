import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  BookOpenCheck,
  CalendarClock,
  ChevronRight,
  CircleDollarSign,
  Database,
  Flame,
  Landmark,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  WalletCards,
  Waves,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import dashboardData from "@/data/dashboard.json";
import portfolioState from "@/data/portfolio_state.json";

const formatMoney = (value: number) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
  }).format(value);

const asOfDate = new Date(`${dashboardData.as_of}T12:00:00+08:00`);
const fullDate = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "long",
  day: "numeric",
  weekday: "short",
  timeZone: "Asia/Shanghai",
}).format(asOfDate);
const shortDate = dashboardData.as_of.slice(5).replace("-", ".");
const sessionLabels: Record<string, string> = {
  "open-check": "开盘检查",
  "luxembourg-morning": "盘中更新",
  "close-decision": "收盘前决策",
  close: "收盘",
  manual: "手动更新",
};
const sessionLabel = sessionLabels[dashboardData.session] ?? dashboardData.session;
const indices = dashboardData.indices;
const techThemes = dashboardData.tech_themes;
const watchlist = dashboardData.watchlist;
const accounts = portfolioState.accounts.map((account) => ({
  ...account,
  cashLabel: formatMoney(account.cash),
  equityLabel: formatMoney(account.equity),
  marketValueLabel: formatMoney(account.market_value),
  pnlLabel: formatMoney(account.pnl),
  pnlPctLabel: `${account.pnl_pct >= 0 ? "+" : ""}${account.pnl_pct.toFixed(2)}%`,
}));
const totalCash = portfolioState.accounts.reduce((sum, account) => sum + account.cash, 0);
const totalPositions = portfolioState.accounts.reduce((sum, account) => sum + account.positions, 0);

function Change({ value }: { value: string }) {
  const positive = value.trim().startsWith("+");
  return (
    <span className={positive ? "change positive" : "change negative"}>
      {positive ? <ArrowUpRight /> : <ArrowDownRight />}{value}
    </span>
  );
}

export default function Home() {
  return (
    <main className="dashboard-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <div className="dashboard">
        <header className="topbar">
          <a className="brand" href="#top" aria-label="返回看板顶部">
            <span className="brand-mark"><TrendingUp /></span>
            <span><strong>A股策略看板</strong><small>MARKET &amp; PAPER PORTFOLIO</small></span>
          </a>
          <nav aria-label="看板导航">
            <a href="#market">市场</a><a href="#watchlist">关注股</a><a href="#accounts">模拟仓</a><a href="#ledger">台账</a>
          </nav>
          <div className="update-pill"><span className="live-dot" /><span>最近更新</span><strong>{shortDate} {sessionLabel}</strong></div>
        </header>

        <section className="overview" id="top">
          <div className="overview-copy">
            <div className="eyebrow"><CalendarClock /> {fullDate} · {sessionLabel}</div>
            <h1>{dashboardData.headline}</h1>
            <p>{dashboardData.summary}</p>
            <div className="brief-actions">
              <a className="primary-link" href="#accounts">查看模拟仓 <ChevronRight /></a>
              <span><RefreshCw /> 每日卢森堡 06:00 更新</span>
            </div>
          </div>
          <div className="market-gauge" aria-label={`市场温度 ${dashboardData.temperature.score} 分，${dashboardData.temperature.label}`}>
            <div className="gauge-head"><span>市场温度</span><Badge className="neutral-badge" variant="outline">{dashboardData.temperature.label}</Badge></div>
            <div className="gauge-score"><strong>{dashboardData.temperature.score}</strong><span>/ 100</span></div>
            <div className="gauge-track"><i style={{ width: `${dashboardData.temperature.score}%` }} /></div>
            <div className="breadth-row">
              <div><span className="up-dot" />上涨 <strong>{dashboardData.breadth.up.toLocaleString("zh-CN")}</strong></div>
              <div><span className="down-dot" />下跌 <strong>{dashboardData.breadth.down.toLocaleString("zh-CN")}</strong></div>
            </div>
            <div className="gauge-note"><ShieldCheck /> 仓位建议：{dashboardData.temperature.position_note}</div>
          </div>
        </section>

        <section id="market" className="section-block">
          <div className="section-heading"><div><span>01</span><h2>市场脉搏</h2></div><p>指数、成交与跨境资金的收盘快照</p></div>
          <div className="indices-grid">
            {indices.map((item) => <article className="index-card" key={item.name}><span>{item.name}</span><strong>{item.value}</strong><Change value={item.change} /></article>)}
          </div>
          <div className="market-detail-grid">
            <article className="turnover-card feature-card">
              <div className="card-icon"><BarChart3 /></div>
              <div><span className="card-label">全市场成交额</span><div className="big-number">{dashboardData.turnover.display} <small>{dashboardData.turnover.unit}</small></div><p><ArrowDownRight /> 较前一日 {dashboardData.turnover.change_yi >= 0 ? "放量" : "缩量"} {Math.abs(dashboardData.turnover.change_yi)} 亿元（{dashboardData.turnover.change_pct}）</p></div>
              <div className="mini-bars" aria-hidden="true">{[38, 54, 47, 72, 68, 88, 76].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}</div>
            </article>
            <article className="flow-card feature-card">
              <div className="card-icon"><Waves /></div>
              <div className="flow-main"><span className="card-label">互联互通资金</span><div className="flow-row">
                <div><small>北向</small><strong>{dashboardData.flows.northbound}</strong></div><div><small>南向</small><strong className="positive-text">{dashboardData.flows.southbound}</strong></div>
              </div><p>{dashboardData.flows.note}</p></div>
            </article>
          </div>
          <article className="tech-board">
            <div className="tech-board-title"><div><Flame /><span><strong>科技热度雷达</strong><small>策略热度评分，不代表涨跌幅</small></span></div><Badge className="hot-badge">{techThemes[0]?.name ?? "科技"}领跑</Badge></div>
            <div className="theme-list">{techThemes.map((theme) => (
              <div className="theme-row" key={theme.name}>
                <div className={`theme-score ${theme.tone}`}><strong>{theme.score}</strong><span>热度</span></div>
                <div className="theme-copy"><strong>{theme.name}</strong><span>{theme.note}</span></div>
                <Badge className={`theme-badge ${theme.tone}`} variant="outline">{theme.status}</Badge>
                <div className="theme-track"><i className={theme.tone} style={{ width: `${theme.score}%` }} /></div>
              </div>
            ))}</div>
          </article>
        </section>

        <section id="watchlist" className="section-block">
          <div className="section-heading"><div><span>02</span><h2>重点关注</h2></div><p>价格、成交、资金与股息率放在同一张表里</p></div>
          <div className="watch-table-wrap"><Table>
            <TableHeader><TableRow><TableHead>股票</TableHead><TableHead>收盘 / 涨跌</TableHead><TableHead>股息率</TableHead><TableHead>成交额</TableHead><TableHead>资金观察</TableHead><TableHead>结论与原因</TableHead></TableRow></TableHeader>
            <TableBody>{watchlist.map((stock) => <TableRow key={stock.code}>
              <TableCell><div className="stock-name"><strong>{stock.name}</strong><span>{stock.code}</span></div></TableCell>
              <TableCell><div className="stock-price"><strong>¥{stock.price}</strong><Change value={stock.change} /></div></TableCell>
              <TableCell><span className="yield-chip">{stock.dividend_yield}</span></TableCell><TableCell>{stock.turnover}</TableCell><TableCell>{stock.flow}</TableCell>
              <TableCell><div className="verdict"><Badge variant="outline">{stock.verdict}</Badge><span>{stock.reason}</span></div></TableCell>
            </TableRow>)}</TableBody>
          </Table></div>
        </section>

        <section id="accounts" className="section-block">
          <div className="section-heading"><div><span>03</span><h2>模拟账户</h2></div><p>本金均为人民币 100,000 元，未成交信号不计入持仓</p></div>
          <div className="account-grid">{accounts.map((account) => <article className={`account-card ${account.color}`} key={account.name}>
            <div className="account-head"><div className="account-icon"><WalletCards /></div><div><h3>{account.name}</h3><span>{account.tag}</span></div><Badge variant="outline">运行中</Badge></div>
            <div className="account-equity"><span>账户总资产</span><strong>{account.equityLabel}</strong><small>累计收益 {account.pnlPctLabel}</small></div>
            <div className="account-stats"><div><span>可用现金</span><strong>{account.cashLabel}</strong></div><div><span>持仓市值</span><strong>{account.marketValueLabel}</strong></div><div><span>持仓数</span><strong>{account.positions}</strong></div><div><span>累计盈亏</span><strong>{account.pnlLabel}</strong></div></div>
            <div className="next-action"><Zap /><div><span>下一步</span><p>{account.next}</p></div></div>
          </article>)}</div>
        </section>

        <section id="ledger" className="ledger-card">
          <div className="ledger-icon"><Database /></div>
          <div className="ledger-copy"><Badge variant="outline">永久台账</Badge><h2>正式记录从第一笔成交开始</h2><p>初始本金合计 ¥200,000.00；当前 0 笔正式交易、{totalPositions} 个持仓。每笔交易将保留策略、理由、价格、数量、费用和盈亏。</p></div>
          <div className="ledger-status"><div><BookOpenCheck /><span>账本状态</span><strong>已初始化</strong></div><div><CircleDollarSign /><span>现金余额</span><strong>{formatMoney(totalCash)}</strong></div><div><Landmark /><span>正式持仓</span><strong>{totalPositions}</strong></div></div>
        </section>

        <footer><div><Sparkles /> 数据截至 {dashboardData.as_of} {sessionLabel} · 公开行情口径</div><p>本看板仅用于策略研究与模拟交易，不构成投资建议。</p></footer>
      </div>
    </main>
  );
}
