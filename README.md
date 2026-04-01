# 🛒 Shopping Price Analyzer & Recommendation System

A full-stack web application that analyzes product prices, visualizes trends, and provides smart recommendations using real-time data from e-commerce platforms.

---

## 🚀 Features

- 📈 **Price Trend Analysis**  
  Visualizes product price changes over time using interactive charts.

- 🔍 **Smart Product Search**  
  Search products across platforms like Amazon, Flipkart, Myntra, etc.

- 🤖 **Recommendation System**  
  Suggests similar products based on price, brand, and attributes.

- 🖼️ **Product Preview**  
  Displays product images, details, and direct purchase links.

- 🔐 **Authentication**  
  Secure login using Firebase (Google Sign-In supported).

- ☁️ **Cloud Database**  
  Stores user search history using Firebase Firestore.

- 🌐 **Real-Time Data Integration**  
  Fetches live product data using external APIs (RapidAPI).

---

## 🏗️ Tech Stack

### Frontend
- React.js
- CSS (Custom Styling)
- Chart Libraries (Recharts / Chart.js)

### Backend
- Python (Flask)
- REST APIs
- Requests Library

### Database & Auth
- Firebase Authentication
- Firebase Firestore

### APIs
- RapidAPI (Amazon / E-commerce Product APIs)

---

## 📂 Project Structure

Shopping-Analyzer/
│
├── Backend/
│ ├── app.py
│ ├── services/
│ │ └── analysis.py
│ └── data/
│
├── frontend/
│ ├── src/
│ │ ├── pages/
│ │ ├── Components/
│ │ └── styles/
│
└── README.md


---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/shopping-price-analyzer.git
cd shopping-price-analyzer
2️⃣ Backend Setup
cd Backend
pip install -r requirements.txt
python app.py
3️⃣ Frontend Setup
cd frontend
npm install
npm run dev
🔑 Environment Variables

Create a .env file in Backend:

RAPIDAPI_KEY=your_api_key_here
RAPIDAPI_HOST=real-time-amazon-data.p.rapidapi.com
📊 How It Works
User searches for a product
Frontend sends request to Flask backend
Backend fetches real-time data via APIs
Data is processed and returned
Frontend displays:
Price trend graph
Product recommendations
Images and purchase links
🎯 Future Enhancements
📉 Price prediction using Machine Learning
🔔 Price drop alerts
❤️ Wishlist functionality
🔄 Multi-platform price comparison
📱 Mobile app version
📸 Screenshots

Add screenshots of your project here

🧑‍💻 Author

Krishna
