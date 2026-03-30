import React, { useState } from 'react';
import '../styles/SearchBar.css';

const SearchBar = ({ onChange }) => {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) {
      return;
    }

    setIsLoading(true);
    try {
      await onChange(query.trim());
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="search-container">
      <div className="search-header">
        <h2>Analyze a live Amazon product</h2>
        <p>Paste an Amazon product URL for a direct lookup, or type a product name and let the app search Amazon automatically.</p>
      </div>

      <div className="search-mode-card">
        <div className="mode-pill-row">
          <span className="mode-pill active">Amazon URL</span>
          <span className="mode-pill">Product name fallback</span>
          <span className="mode-pill">Live catalogue images</span>
        </div>
        <p className="search-mode-copy">
          URL search is preferred. If the input is not a valid Amazon URL or ASIN, the app will switch to product-name search and build recommendations from Amazon results.
        </p>
      </div>

      <div className="search-input-wrapper">
        <div className="search-input-group">
          <input
            type="text"
            className="search-input"
            placeholder="Paste Amazon link or try 'iPhone 15', 'laptop sleeve', 'Samsung monitor'..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            className="search-button"
            onClick={handleSearch}
            disabled={isLoading || !query.trim()}
            type="button"
          >
            {isLoading ? (
              <>
                <span className="spinner"></span>
                Analyzing
              </>
            ) : (
              <>Run Amazon Analysis</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SearchBar;
