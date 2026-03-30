import React from 'react';
import { Bar, Line } from 'react-chartjs-2';
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import '../styles/PriceChart.css';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler);

const formatCurrency = (value) =>
  `Rs. ${Number(value).toLocaleString('en-IN', {
    maximumFractionDigits: 2,
  })}`;

const PriceChart = ({ data = [], forecast = [], chartType = 'line' }) => {
  const labels = [...data.map((item) => item.date), ...forecast.map((item) => item.date)];
  const historicalValues = [...data.map((item) => item.price), ...forecast.map(() => null)];
  const forecastValues = [...data.map(() => null), ...forecast.map((item) => item.price)];

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Historical Price',
        data: historicalValues,
        borderColor: 'rgba(15, 118, 110, 1)',
        backgroundColor: 'rgba(15, 118, 110, 0.12)',
        borderWidth: 3,
        fill: chartType === 'line',
        tension: 0.32,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
      {
        label: 'Forecast',
        data: forecastValues,
        borderColor: 'rgba(249, 115, 22, 1)',
        backgroundColor: 'rgba(249, 115, 22, 0.18)',
        borderDash: [8, 6],
        borderWidth: 3,
        fill: false,
        tension: 0.32,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
      },
      tooltip: {
        callbacks: {
          label: (context) => `${context.dataset.label}: ${formatCurrency(context.parsed.y)}`,
        },
      },
    },
    scales: {
      y: {
        ticks: {
          callback: (value) => formatCurrency(value),
        },
      },
    },
  };

  if (!data.length) {
    return (
      <div className="price-chart-container">
        <div className="chart-empty-state">
          <p>Search for a product to see price history and forecast data.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="price-chart-container">
      <div className="chart-caption-row">
        <div>
          <h3>Price trajectory</h3>
          <p>Historical points are modelled from live Amazon price and peer signals. The orange line projects the next buying window.</p>
        </div>
      </div>
      <div className="chart-wrapper">{chartType === 'line' ? <Line data={chartData} options={options} /> : <Bar data={chartData} options={options} />}</div>
    </div>
  );
};

export default PriceChart;
