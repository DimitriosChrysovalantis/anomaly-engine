import { useState, useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import { AlertTriangle, Activity, Target, DollarSign, TrendingDown, Download, Percent, ShieldAlert, Cpu } from 'lucide-react';

export default function App() {
  const [data, setData] = useState([]);
  const [metrics, setMetrics] = useState({ sharpe: 0, max_drawdown: 0, win_rate: 0, total_trades: 0, optimal_sl: 0, optimal_tp: 0 });
  const [loading, setLoading] = useState(true);
  
  const [windowDays, setWindowDays] = useState(30);
  const [driverFilter, setDriverFilter] = useState('ALL');

  const wsRef = useRef(null);
  
  // TradingView Chart Refs
  const chartContainerRef = useRef();
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const isChartInitialized = useRef(false);

  useEffect(() => {
    const ws = new WebSocket('ws://127.0.0.1:8000/ws/anomalies');
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.data && payload.metrics) {
        setData(payload.data);
        setMetrics(payload.metrics);
        setLoading(false);
      }
    };

    ws.onopen = () => {
      ws.send(JSON.stringify({ window_days: 30 }));
    };

    return () => ws.close();
  }, []);

  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ window_days: windowDays }));
    }
  }, [windowDays]);

  // TradingView Rendering Engine
  useEffect(() => {
    if (!data.length || !chartContainerRef.current) return;

    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#94a3b8' },
        grid: {
          vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
          horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
        },
        timeScale: { timeVisible: true, secondsVisible: false },
        crosshair: { mode: 0 }
      });

      seriesRef.current = chartRef.current.addCandlestickSeries({
        upColor: '#10b981', 
        downColor: '#f43f5e', 
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#f43f5e',
      });

      const handleResize = () => {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      };
      window.addEventListener('resize', handleResize);
    }

    const formattedData = [];
    const seenTimes = new Set();
    
    [...data]
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .forEach(d => {
        const time = Math.floor(new Date(d.timestamp).getTime() / 1000);
        if (!seenTimes.has(time)) {
          seenTimes.add(time);
          formattedData.push({
            time,
            open: d.Open || d.value,
            high: d.High || d.value,
            low: d.Low || d.value,
            close: d.value
          });
        }
      });

    seriesRef.current.setData(formattedData);

    const markers = [];
    const seenMarkerTimes = new Set();

    [...data]
      .filter(d => d.is_anomaly)
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .forEach(d => {
        const time = Math.floor(new Date(d.timestamp).getTime() / 1000);
        if (!seenMarkerTimes.has(time)) {
          seenMarkerTimes.add(time);
          markers.push({
            time,
            position: d.z_score > 0 ? 'aboveBar' : 'belowBar',
            color: d.z_score > 0 ? '#f43f5e' : '#3b82f6', 
            shape: d.z_score > 0 ? 'arrowDown' : 'arrowUp',
            text: 'Break'
          });
        }
      });

    seriesRef.current.setMarkers(markers);

    if (!isChartInitialized.current) {
      chartRef.current.timeScale().fitContent();
      isChartInitialized.current = true;
    }

  }, [data]);

  const exportCSV = () => {
    if (!data.length) return;
    const headers = ["timestamp", "open", "high", "low", "close", "vix_value", "z_score", "is_anomaly", "anomaly_driver", "simulated_pnl", "cumulative_pnl"];
    const rows = data.map(d => headers.map(h => {
        if (h === 'open') return d.Open || d.value;
        if (h === 'high') return d.High || d.value;
        if (h === 'low') return d.Low || d.value;
        if (h === 'close') return d.value;
        return d[h] ?? '';
    }).join(','));
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(','), ...rows].join('\n');
    const link = document.createElement("a");
    link.setAttribute("href", encodeURI(csvContent));
    link.setAttribute("download", `anomaly_backtest_${windowDays}d.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) return <div className="flex h-screen items-center justify-center text-xl text-white font-mono">Running Grid Search Optimizer...</div>;

  const latest = data[data.length - 1] || {};
  const allAnomalies = data.filter(d => d.is_anomaly).reverse();
  const filteredAnomalies = driverFilter === 'ALL' 
    ? allAnomalies 
    : allAnomalies.filter(d => d.anomaly_driver === driverFilter);

  const totalPnL = latest.cumulative_pnl || 0;

  return (
    <div className="p-8 max-w-[1500px] mx-auto space-y-6 bg-slate-950 text-slate-100 min-h-screen">
      
      {/* Header & Controls Bar */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 mb-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">NQ Futures <span className="text-blue-400">Quant Terminal</span></h1>
          <p className="text-sm text-gray-400 mt-1">Real-time isolation forest backtester & trade execution workbench</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex bg-white/5 border border-white/10 p-1 rounded-xl">
            {[7, 14, 30].map((days) => (
              <button
                key={days}
                onClick={() => setWindowDays(days)}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-colors ${
                  windowDays === days ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
              >
                {days}D
              </button>
            ))}
          </div>

          <button 
            onClick={exportCSV}
            className="flex items-center gap-2 bg-blue-500/10 border border-blue-500/30 text-blue-400 hover:bg-blue-500/20 px-4 py-2 rounded-xl text-xs font-semibold transition-colors"
          >
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      {/* Auto-Optimizer Display Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-2xl bg-blue-900/10 border border-blue-500/20 backdrop-blur-md">
        <div className="flex flex-col gap-1 justify-center">
          <div className="flex items-center gap-2 text-blue-400 font-semibold text-sm">
            <Cpu size={16} /> Grid Search Optimized Parameters
          </div>
          <div className="text-xs text-gray-400">Calculated over {windowDays}-day rolling window</div>
        </div>

        <div className="flex flex-col gap-1 border-l border-white/10 pl-4">
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <ShieldAlert size={14}/> Algorithm Stop-Loss
          </div>
          <div className="text-2xl font-bold text-rose-400">{metrics.optimal_sl?.toFixed(1)}%</div>
        </div>

        <div className="flex flex-col gap-1 border-l border-white/10 pl-4">
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <Percent size={14}/> Algorithm Take-Profit
          </div>
          <div className="text-2xl font-bold text-emerald-400">{metrics.optimal_tp?.toFixed(1)}%</div>
        </div>
      </div>

      {/* Performance Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
          <div className="text-xs text-gray-400 mb-1 flex items-center gap-1"><Activity size={14}/> Price</div>
          <div className="text-xl font-light">${latest.value?.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
        </div>
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
          <div className="text-xs text-gray-400 mb-1 flex items-center gap-1"><AlertTriangle size={14} className="text-rose-400"/> Trades</div>
          <div className="text-xl font-light text-rose-400">{metrics.total_trades}</div>
        </div>
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
          <div className="text-xs text-gray-400 mb-1 flex items-center gap-1"><DollarSign size={14} className={totalPnL >= 0 ? "text-emerald-400" : "text-rose-400"}/> Cum PnL</div>
          <div className={`text-xl font-light ${totalPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {totalPnL >= 0 ? '+' : ''}${totalPnL.toLocaleString(undefined, {minimumFractionDigits: 2})}
          </div>
        </div>
        <div className="p-4 rounded-2xl bg-white/5 border border-blue-500/20">
          <div className="text-xs text-gray-400 mb-1 flex items-center gap-1"><Percent size={14} className="text-blue-400"/> Win Rate</div>
          <div className="text-xl font-mono text-blue-300">{metrics.win_rate.toFixed(1)}%</div>
        </div>
        <div className="p-4 rounded-2xl bg-white/5 border border-emerald-500/20">
          <div className="text-xs text-gray-400 mb-1 flex items-center gap-1"><Target size={14} className="text-emerald-400"/> Sharpe</div>
          <div className="text-xl font-mono text-emerald-300">{metrics.sharpe.toFixed(2)}</div>
        </div>
        <div className="p-4 rounded-2xl bg-white/5 border border-rose-500/20">
          <div className="text-xs text-gray-400 mb-1 flex items-center gap-1"><TrendingDown size={14} className="text-rose-400"/> Max DD</div>
          <div className="text-xl font-mono text-rose-300">${Math.abs(metrics.max_drawdown).toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
        </div>
      </div>

      {/* Main Container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* TradingView Chart Container */}
        <div className="lg:col-span-2 p-1 rounded-2xl bg-white/5 border border-white/10 h-[620px] flex flex-col relative overflow-hidden">
          <div ref={chartContainerRef} className="w-full h-full absolute inset-0 rounded-xl overflow-hidden" />
        </div>

        {/* Filterable Incident Log */}
        <div className="p-6 rounded-2xl bg-white/5 border border-white/10 h-[620px] flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-200">Execution Log</h2>
            <select 
              value={driverFilter} 
              onChange={(e) => setDriverFilter(e.target.value)}
              className="bg-slate-900 border border-white/10 text-xs text-gray-300 rounded-lg px-2 py-1 outline-none cursor-pointer"
            >
              <option value="ALL">All Drivers</option>
              <option value="Macro Volatility (VIX)">Macro Volatility (VIX)</option>
              <option value="Price Deviation">Price Deviation</option>
              <option value="Liquidity Spike">Liquidity Spike</option>
              <option value="Microstructure Break">Microstructure Break</option>
            </select>
          </div>

          <div className="overflow-y-auto pr-2 space-y-3 flex-1">
            {filteredAnomalies.map((incident, i) => (
              <div key={i} className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
                <div className="flex justify-between items-start mb-1">
                  <div>
                    <div className="text-[11px] text-gray-400">{incident.timestamp}</div>
                    <div className="font-semibold text-sm text-slate-100">${incident.value.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-gray-500 uppercase block">Z-Score</span>
                    <span className="font-mono text-rose-400 text-xs font-semibold">{incident.z_score.toFixed(2)}</span>
                  </div>
                </div>
                <div className="pt-2 mt-2 border-t border-slate-800/80 flex justify-between items-center">
                  <span className="text-xs text-blue-400 font-medium">{incident.anomaly_driver}</span>
                  <span className={`font-mono text-xs font-bold ${incident.simulated_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {incident.simulated_pnl >= 0 ? '+' : ''}${incident.simulated_pnl.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}