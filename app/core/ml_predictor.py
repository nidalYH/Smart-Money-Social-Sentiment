"""
Machine Learning Price Prediction Engine
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import os

logger = logging.getLogger(__name__)

@dataclass
class MLPrediction:
    """Machine Learning prediction result"""
    symbol: str
    predicted_price: float
    confidence: float
    time_horizon: str  # 1h, 4h, 1d, 1w
    features_used: List[str]
    model_type: str
    timestamp: datetime

class MLPredictor:
    """Machine Learning price prediction engine"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        self.model_performance = {}
        
    def create_features(self, price_data: Dict) -> pd.DataFrame:
        """Create features for ML model"""
        try:
            prices = price_data.get('prices', [])
            volumes = price_data.get('volumes', [])
            timestamps = price_data.get('timestamps', [])
            
            if len(prices) < 50:
                return pd.DataFrame()
            
            df = pd.DataFrame({
                'price': prices,
                'volume': volumes,
                'timestamp': timestamps
            })
            
            # Price-based features
            df['price_change'] = df['price'].pct_change()
            df['price_change_abs'] = df['price_change'].abs()
            df['log_price'] = np.log(df['price'])
            df['price_ma_5'] = df['price'].rolling(5).mean()
            df['price_ma_10'] = df['price'].rolling(10).mean()
            df['price_ma_20'] = df['price'].rolling(20).mean()
            df['price_std_5'] = df['price'].rolling(5).std()
            df['price_std_10'] = df['price'].rolling(10).std()
            df['price_std_20'] = df['price'].rolling(20).std()
            
            # Volume-based features
            df['volume_ma_5'] = df['volume'].rolling(5).mean()
            df['volume_ma_10'] = df['volume'].rolling(10).mean()
            df['volume_std_5'] = df['volume'].rolling(5).std()
            df['volume_price_ratio'] = df['volume'] / df['price']
            
            # Technical indicators
            df['rsi_14'] = self._calculate_rsi(df['price'], 14)
            df['macd'] = self._calculate_macd(df['price'])
            df['bb_upper'] = self._calculate_bollinger_upper(df['price'], 20, 2)
            df['bb_lower'] = self._calculate_bollinger_lower(df['price'], 20, 2)
            df['bb_position'] = (df['price'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Time-based features
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            
            # Lag features
            for lag in [1, 2, 3, 5, 10]:
                df[f'price_lag_{lag}'] = df['price'].shift(lag)
                df[f'volume_lag_{lag}'] = df['volume'].shift(lag)
                df[f'price_change_lag_{lag}'] = df['price_change'].shift(lag)
            
            # Rolling statistics
            for window in [5, 10, 20]:
                df[f'price_skew_{window}'] = df['price'].rolling(window).skew()
                df[f'price_kurt_{window}'] = df['price'].rolling(window).kurt()
                df[f'volume_skew_{window}'] = df['volume'].rolling(window).skew()
                df[f'volume_kurt_{window}'] = df['volume'].rolling(window).kurt()
            
            # Target variable (future price)
            df['target_1h'] = df['price'].shift(-1)  # 1 hour ahead
            df['target_4h'] = df['price'].shift(-4)  # 4 hours ahead
            df['target_1d'] = df['price'].shift(-24)  # 1 day ahead
            df['target_1w'] = df['price'].shift(-168)  # 1 week ahead
            
            # Price change targets
            df['target_change_1h'] = (df['target_1h'] - df['price']) / df['price']
            df['target_change_4h'] = (df['target_4h'] - df['price']) / df['price']
            df['target_change_1d'] = (df['target_1d'] - df['price']) / df['price']
            df['target_change_1w'] = (df['target_1w'] - df['price']) / df['price']
            
            return df.dropna()
            
        except Exception as e:
            logger.error(f"Error creating features: {e}")
            return pd.DataFrame()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        return ema_fast - ema_slow
    
    def _calculate_bollinger_upper(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> pd.Series:
        """Calculate Bollinger Bands upper"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        return sma + (std * std_dev)
    
    def _calculate_bollinger_lower(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> pd.Series:
        """Calculate Bollinger Bands lower"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        return sma - (std * std_dev)
    
    def train_model(self, symbol: str, price_data: Dict, model_type: str = "random_forest") -> bool:
        """Train ML model for price prediction"""
        try:
            df = self.create_features(price_data)
            if df.empty:
                return False
            
            # Feature columns (exclude target and timestamp)
            feature_cols = [col for col in df.columns if not col.startswith('target') and col != 'timestamp']
            X = df[feature_cols]
            
            # Train models for different time horizons
            horizons = ['1h', '4h', '1d', '1w']
            
            for horizon in horizons:
                target_col = f'target_change_{horizon}'
                if target_col not in df.columns:
                    continue
                
                y = df[target_col].dropna()
                X_aligned = X.loc[y.index]
                
                if len(y) < 100:  # Need enough data
                    continue
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X_aligned, y, test_size=0.2, random_state=42
                )
                
                # Scale features
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
                
                # Train model
                if model_type == "random_forest":
                    model = RandomForestRegressor(
                        n_estimators=100,
                        max_depth=10,
                        random_state=42,
                        n_jobs=-1
                    )
                elif model_type == "gradient_boosting":
                    model = GradientBoostingRegressor(
                        n_estimators=100,
                        max_depth=6,
                        random_state=42
                    )
                elif model_type == "ridge":
                    model = Ridge(alpha=1.0)
                else:
                    model = LinearRegression()
                
                model.fit(X_train_scaled, y_train)
                
                # Evaluate model
                y_pred = model.predict(X_test_scaled)
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                # Store model and scaler
                model_key = f"{symbol}_{horizon}_{model_type}"
                self.models[model_key] = model
                self.scalers[model_key] = scaler
                self.model_performance[model_key] = {
                    'mse': mse,
                    'r2': r2,
                    'feature_importance': dict(zip(feature_cols, model.feature_importances_)) if hasattr(model, 'feature_importances_') else {}
                }
                
                logger.info(f"Trained {model_type} model for {symbol} {horizon}: R² = {r2:.4f}, MSE = {mse:.6f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training model for {symbol}: {e}")
            return False
    
    def predict_price(self, symbol: str, price_data: Dict, time_horizon: str = "1h") -> Optional[MLPrediction]:
        """Predict future price using trained model"""
        try:
            model_key = f"{symbol}_{time_horizon}_random_forest"
            
            if model_key not in self.models:
                # Try to train model if not exists
                if not self.train_model(symbol, price_data):
                    return None
            
            # Create features for prediction
            df = self.create_features(price_data)
            if df.empty:
                return None
            
            feature_cols = [col for col in df.columns if not col.startswith('target') and col != 'timestamp']
            X_latest = df[feature_cols].iloc[-1:].values
            
            # Scale features
            scaler = self.scalers[model_key]
            X_scaled = scaler.transform(X_latest)
            
            # Make prediction
            model = self.models[model_key]
            predicted_change = model.predict(X_scaled)[0]
            
            # Convert change to price
            current_price = price_data['prices'][-1]
            predicted_price = current_price * (1 + predicted_change)
            
            # Calculate confidence based on model performance
            performance = self.model_performance.get(model_key, {})
            confidence = min(max(performance.get('r2', 0.5), 0.1), 0.95)
            
            return MLPrediction(
                symbol=symbol,
                predicted_price=predicted_price,
                confidence=confidence,
                time_horizon=time_horizon,
                features_used=feature_cols,
                model_type="random_forest",
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error predicting price for {symbol}: {e}")
            return None
    
    def get_feature_importance(self, symbol: str, time_horizon: str = "1h") -> Dict[str, float]:
        """Get feature importance for trained model"""
        model_key = f"{symbol}_{time_horizon}_random_forest"
        return self.model_performance.get(model_key, {}).get('feature_importance', {})
    
    def save_models(self, filepath: str):
        """Save trained models to disk"""
        try:
            os.makedirs(filepath, exist_ok=True)
            
            for model_key, model in self.models.items():
                model_path = os.path.join(filepath, f"{model_key}_model.joblib")
                joblib.dump(model, model_path)
            
            for scaler_key, scaler in self.scalers.items():
                scaler_path = os.path.join(filepath, f"{scaler_key}_scaler.joblib")
                joblib.dump(scaler, scaler_path)
            
            logger.info(f"Models saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def load_models(self, filepath: str):
        """Load trained models from disk"""
        try:
            for model_key in self.models.keys():
                model_path = os.path.join(filepath, f"{model_key}_model.joblib")
                scaler_path = os.path.join(filepath, f"{model_key}_scaler.joblib")
                
                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    self.models[model_key] = joblib.load(model_path)
                    self.scalers[model_key] = joblib.load(scaler_path)
            
            logger.info(f"Models loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    def get_model_performance(self) -> Dict[str, Dict]:
        """Get performance metrics for all models"""
        return self.model_performance
