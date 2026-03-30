import React, { useState } from 'react';
import '../styles/Recommendations.css';

const formatCurrency = (value) =>
  `Rs. ${Number(value || 0).toLocaleString('en-IN', {
    maximumFractionDigits: 2,
  })}`;

const Recommendations = ({ data, onToggleWishlist, user, wishlist }) => {
  const [expandedCard, setExpandedCard] = useState(null);

  if (!data || data.length === 0) {
    return (
      <section className="recommendations-container">
        <div className="recommendations-header">
          <h2>Amazon Recommendations</h2>
          <p>Similar Amazon listings will appear here with live product images, price context, and save actions.</p>
        </div>
        <div className="empty-recommendations">
          <p>Run an analysis to unlock Amazon recommendations.</p>
        </div>
      </section>
    );
  }

  const averagePrice = data.reduce((sum, item) => sum + (item.price || 0), 0) / data.length;

  return (
    <section className="recommendations-container">
      <div className="recommendations-header">
        <h2>Amazon Recommendations</h2>
        <p>These listings are the closest live Amazon matches for the active product and buying window.</p>
      </div>

      <div className="recommendations-grid">
        {data.map((item, index) => {
          const priceGap = averagePrice ? (((item.price || 0) - averagePrice) / averagePrice) * 100 : 0;
          const isExpanded = expandedCard === index;
          const isWishlisted = wishlist.some(
            (wishlistItem) =>
              (wishlistItem.asin && wishlistItem.asin === item.asin) ||
              (wishlistItem.name === item.name && wishlistItem.platform === item.platform && wishlistItem.brand === item.brand)
          );

          return (
            <div
              key={item.asin || `${item.name}-${item.platform}`}
              className={`product-card ${isExpanded ? 'expanded' : ''}`}
              onClick={() => setExpandedCard(isExpanded ? null : index)}
            >
              <div className="card-header">
                <div className="similarity-badge">
                  <span className="similarity-score">{Math.round(item.similarity || 0)}%</span>
                  <span className="similarity-label">Match</span>
                </div>
                <div className="card-actions">
                  <button className="action-btn amazon-btn" title="Amazon listing" type="button">
                    A
                  </button>
                  <button
                    className={`action-btn favorite-btn ${isWishlisted ? 'active' : ''}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      onToggleWishlist?.(item);
                    }}
                    title={user ? 'Toggle wishlist' : 'Sign in to use wishlist'}
                    type="button"
                  >
                    {isWishlisted ? 'S' : '+'}
                  </button>
                </div>
              </div>

              <div className="product-image-shell">
                {item.image ? <img alt={item.name} className="product-image" src={item.image} /> : <div className="product-image-placeholder">A</div>}
              </div>

              <div className="product-content">
                <div className="product-meta-row">
                  <span className="market-pill">{item.platform}</span>
                  <span className="rating-pill">{item.rating ? `${item.rating}/5` : 'No rating'}</span>
                </div>
                <h3 className="product-name">{item.name}</h3>
                <p className="product-description">{item.description || 'Live Amazon catalogue result.'}</p>

                <div className="badge-row">
                  {item.isBestSeller && <span className="listing-pill success">Best seller</span>}
                  {item.isAmazonChoice && <span className="listing-pill info">Amazon choice</span>}
                  {item.isPrime && <span className="listing-pill neutral">Prime</span>}
                </div>

                <div className="product-info">
                  <div className="info-row">
                    <span className="label">Brand</span>
                    <span className="value">{item.brand || 'Amazon'}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">Category</span>
                    <span className="value">{item.category || 'Amazon catalogue'}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">Type</span>
                    <span className="value">{item.productType || 'Listing'}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">Color</span>
                    <span className="value">{item.color || 'Mixed'}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">Discount</span>
                    <span className="value discount-value">{item.discount ? `${item.discount}% off` : item.discountText || 'Live price'}</span>
                  </div>
                </div>
              </div>

              <div className="product-footer">
                <div className="price-section">
                  <div className="current-price">{formatCurrency(item.price)}</div>
                  <div className={`price-comparison ${priceGap > 0 ? 'higher' : 'lower'}`}>
                    {priceGap > 0 ? '+' : ''}
                    {priceGap.toFixed(0)}% vs similar items
                  </div>
                </div>
                <div className="footer-actions">
                  <button
                    className="view-btn secondary"
                    onClick={(event) => {
                      event.stopPropagation();
                      onToggleWishlist?.(item);
                    }}
                    type="button"
                  >
                    {user ? (isWishlisted ? 'Saved' : 'Save item') : 'Sign in to save'}
                  </button>
                  {item.url && (
                    <button
                      className="view-btn"
                      onClick={(event) => {
                        event.stopPropagation();
                        window.open(item.url, '_blank', 'noopener,noreferrer');
                      }}
                      type="button"
                    >
                      Open Amazon
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default Recommendations;
