import React, { useState } from 'react';
import SearchBar from '../Compoonents/SearchBar';
import PriceChart from '../Compoonents/PriceChart';
import Recommendations from '../Compoonents/Recommendations';
import '../styles/Dashboard.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';

const emptyResult = {
  product: null,
  priceData: [],
  prediction: { nextPrice: null, forecast: [], confidence: 'low' },
  recommendations: [],
  summary: {},
  insights: [],
};

const formatCurrency = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'Rs. 0';
  }

  return `Rs. ${Number(value).toLocaleString('en-IN', {
    maximumFractionDigits: 2,
  })}`;
};

const formatRelativeDate = (value) => {
  if (!value) {
    return 'Just now';
  }

  const date = typeof value?.toDate === 'function' ? value.toDate() : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Just now';
  }

  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const Dashboard = ({ onSaveSearch, onToggleWishlist, searchHistory, user, wishlist }) => {
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [chartType, setChartType] = useState('line');
  const [result, setResult] = useState(emptyResult);
  const [wishlistMessage, setWishlistMessage] = useState('');

  const handleSearch = async (query) => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }

    setIsSearching(true);
    setError(null);
    setSearchQuery(trimmedQuery);
    setWishlistMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/search?product=${encodeURIComponent(trimmedQuery)}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Search failed. Please confirm the backend is running and try again.');
      }

      if (!data.priceData?.length) {
        throw new Error('No matching Amazon product data was found for that search.');
      }

      const nextResult = {
        product: data.product ?? null,
        priceData: data.priceData ?? [],
        prediction: data.prediction ?? emptyResult.prediction,
        recommendations: data.recommendations ?? [],
        summary: data.summary ?? {},
        insights: data.insights ?? [],
      };

      setResult(nextResult);

      await onSaveSearch?.({
        query: trimmedQuery,
        platform: 'amazon',
        asin: nextResult.product?.asin ?? null,
        productName: nextResult.product?.name ?? trimmedQuery,
        currentPrice: nextResult.summary.currentPrice ?? null,
        resultCount: nextResult.summary.resultCount ?? 0,
        image: nextResult.product?.image ?? '',
        productUrl: nextResult.product?.url ?? '',
      });
    } catch (err) {
      setError(err.message || 'Failed to fetch analysis data.');
      setResult(emptyResult);
    } finally {
      setIsSearching(false);
    }
  };

  const handleWishlistToggle = async (item) => {
    if (!user) {
      setWishlistMessage('Sign in to save Amazon items to your wishlist.');
      return;
    }

    const isSaved = await onToggleWishlist?.(item);

    if (isSaved === undefined) {
      return;
    }

    setWishlistMessage(isSaved ? `${item.name} added to wishlist.` : `${item.name} removed from wishlist.`);
  };

  const hasResults = result.priceData.length > 0;
  const combinedSeries = [...result.priceData, ...(result.prediction?.forecast ?? [])];
  const lowestWindows = [...combinedSeries].sort((left, right) => left.price - right.price).slice(0, 4);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <p className="eyebrow">Amazon Price Intelligence</p>
          <h1 className="main-title">GetOne4u Amazon Insight Studio</h1>
          <p className="subtitle">
            Live Amazon catalogue data powers URL search, product discovery, peer recommendations, and an ML-guided buying window.
          </p>
        </div>
      </header>

      <main className="dashboard-main">
        <section className="search-section">
          <SearchBar onChange={handleSearch} />
        </section>

        <section className="sync-grid">
          <article className="sync-card">
            <div className="sync-card-header">
              <h3>Recent Amazon Searches</h3>
              <span className="sync-badge">{user ? 'Synced' : 'Guest mode'}</span>
            </div>
            {searchHistory.length ? (
              <div className="sync-list">
                {searchHistory.map((item) => (
                  <button
                    key={item.id}
                    className="sync-list-item"
                    onClick={() => handleSearch(item.query || item.productName || '')}
                    type="button"
                  >
                    <strong>{item.productName || item.query}</strong>
                    <span>amazon</span>
                    <small>{formatRelativeDate(item.timestamp)}</small>
                  </button>
                ))}
              </div>
            ) : (
              <p className="sync-empty">{user ? 'Your Firebase Amazon search history will appear here.' : 'Sign in to store Amazon search history in Firestore.'}</p>
            )}
          </article>

          <article className="sync-card">
            <div className="sync-card-header">
              <h3>Wishlist</h3>
              <span className="sync-badge accent">{wishlist.length} saved</span>
            </div>
            {wishlist.length ? (
              <div className="sync-list">
                {wishlist.map((item) => (
                  <div key={item.id} className="sync-list-item static with-thumb">
                    {item.image ? <img alt={item.name} className="sync-thumb" src={item.image} /> : <div className="sync-thumb fallback">A</div>}
                    <div>
                      <strong>{item.name}</strong>
                      <span>{item.brand || 'Amazon'} | amazon</span>
                      <small>{formatCurrency(item.price)}</small>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="sync-empty">{user ? 'Tap the wishlist button on any recommendation to save it.' : 'Sign in to keep favourite Amazon items in your wishlist.'}</p>
            )}
          </article>
        </section>

        {wishlistMessage && <div className="status-banner">{wishlistMessage}</div>}

        {error && (
          <div className="error-banner">
            <span className="error-icon">!</span>
            <p>{error}</p>
            <button onClick={() => setError(null)} className="close-error" type="button">
              x
            </button>
          </div>
        )}

        {searchQuery && (
          <div className="search-context">
            <div className="search-result-header">
              <div>
                <h2>
                  Results for <span className="query-highlight">{searchQuery}</span>
                </h2>
                <p className="result-subtext">
                  Source: <strong>Amazon live data</strong>
                  {result.product?.name ? ` | Focus item: ${result.product.name}` : ''}
                </p>
              </div>
              <div className="chart-controls">
                <button
                  className={`chart-type-btn ${chartType === 'line' ? 'active' : ''}`}
                  onClick={() => setChartType('line')}
                  type="button"
                >
                  Line View
                </button>
                <button
                  className={`chart-type-btn ${chartType === 'bar' ? 'active' : ''}`}
                  onClick={() => setChartType('bar')}
                  type="button"
                >
                  Bar View
                </button>
              </div>
            </div>

            {result.product && (
              <section className="hero-product-card">
                <div className="hero-product-media">
                  {result.product.image ? <img alt={result.product.name} src={result.product.image} /> : <div className="hero-product-fallback">A</div>}
                </div>
                <div className="hero-product-copy">
                  <div className="hero-pill-row">
                    <span className="hero-pill">Amazon</span>
                    <span className="hero-pill">{result.product.brand || 'Brand not listed'}</span>
                    <span className="hero-pill">{result.product.rating ? `${result.product.rating}/5 rating` : 'Rating unavailable'}</span>
                  </div>
                  <h3>{result.product.name}</h3>
                  <p>{result.product.description || 'Live product details pulled from Amazon.'}</p>
                  <div className="hero-meta-grid">
                    <div>
                      <span>Current price</span>
                      <strong>{formatCurrency(result.summary.currentPrice)}</strong>
                    </div>
                    <div>
                      <span>Availability</span>
                      <strong>{result.summary.currentAvailability || 'Availability not listed'}</strong>
                    </div>
                    <div>
                      <span>Best modelled month</span>
                      <strong>{result.summary.bestBuyingMonth || 'N/A'}</strong>
                    </div>
                  </div>
                  {result.product.url && (
                    <button className="hero-link-btn" onClick={() => window.open(result.product.url, '_blank', 'noopener,noreferrer')} type="button">
                      Open on Amazon
                    </button>
                  )}
                </div>
              </section>
            )}

            {hasResults && result.summary.recommendationLine && (
              <section className="summary-hero-card">
                <p className="summary-hero-label">ML Recommendation</p>
                <h3>{result.summary.recommendationLine}</h3>
              </section>
            )}

            <section className="chart-section">
              {isSearching ? (
                <div className="loading-state">
                  <div className="loading-spinner"></div>
                  <p>Analyzing live Amazon pricing and modelling the next buying window...</p>
                </div>
              ) : hasResults ? (
                <div className="chart-container">
                  <PriceChart
                    data={result.priceData}
                    forecast={result.prediction?.forecast ?? []}
                    chartType={chartType}
                  />

                  <div className="chart-stats">
                    <div className="stat">
                      <span className="stat-label">Current Price</span>
                      <span className="stat-value">{formatCurrency(result.summary.currentPrice)}</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Lowest Modeled</span>
                      <span className="stat-value">{formatCurrency(result.summary.lowestPrice)}</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Highest Modeled</span>
                      <span className="stat-value">{formatCurrency(result.summary.highestPrice)}</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Forecast Next Month</span>
                      <span className="stat-value">{formatCurrency(result.prediction?.nextPrice)}</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Best Buy Month</span>
                      <span className="stat-value compact">{result.summary.bestBuyingMonth || 'N/A'}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="empty-chart-state">
                  <p>No price data available for this search.</p>
                </div>
              )}
            </section>

            {hasResults && (
              <section className="analytics-grid">
                <article className="insight-card">
                  <h3>Buying Window</h3>
                  <p>
                    Best discount period: <strong>{result.summary.bestBuyingMonth || 'N/A'}</strong>
                  </p>
                  <p>
                    Likely campaign: <strong>{result.summary.bestBuyingEvent || 'N/A'}</strong>
                  </p>
                  <p>
                    Average discount: <strong>{result.summary.averageDiscount ?? 0}%</strong>
                  </p>
                </article>

                <article className="insight-card">
                  <h3>Forecast Confidence</h3>
                  <p className="confidence-badge">{result.prediction?.confidence || 'low'}</p>
                  <p>
                    Historical points used: <strong>{result.priceData.length}</strong>
                  </p>
                  <p>
                    Live catalogue matches: <strong>{result.summary.resultCount ?? 0}</strong>
                  </p>
                </article>

                <article className="insight-card insight-card-wide">
                  <h3>Lowest Price Windows</h3>
                  <ul className="insight-list">
                    {lowestWindows.map((point) => (
                      <li key={`${point.kind}-${point.date}`}>
                        <span>{point.date}</span>
                        <strong>{formatCurrency(point.price)}</strong>
                      </li>
                    ))}
                  </ul>
                </article>
              </section>
            )}

            {result.insights.length > 0 && (
              <section className="insights-panel">
                <h3>Machine Learning Notes</h3>
                <div className="insight-pill-row">
                  {result.insights.map((insight) => (
                    <div key={insight} className="insight-pill">
                      {insight}
                    </div>
                  ))}
                </div>
              </section>
            )}

            <section className="recommendations-section">
              <Recommendations
                data={result.recommendations}
                onToggleWishlist={handleWishlistToggle}
                user={user}
                wishlist={wishlist}
              />
            </section>
          </div>
        )}
      </main>

      <footer className="dashboard-footer">
        <p>2026 GetOne4u | Firebase keeps your activity live while the Amazon-aware Flask engine handles pricing intelligence.</p>
      </footer>
    </div>
  );
};

export default Dashboard;
