"""
Anomaly Detection algorithms for microgrid data
Implements: Autoencoder, PCA, One Class SVM, Isolation Forest
"""
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score
from tensorflow import keras
from tensorflow.keras import layers, Model
import joblib
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class AutoencoderAnomalyDetector:
    """
    Autoencoder for anomaly detection in microgrid data.
    Learns compressed representation of normal patterns; high reconstruction error indicates anomaly.
    """
    
    def __init__(self, input_dim: int, latent_dim: int = 8, 
                 encoding_layers: List[int] = [32, 16],
                 threshold_percentile: float = 95.0):
        """
        Initialize Autoencoder
        
        Args:
            input_dim: Number of input features
            latent_dim: Dimension of latent/bottleneck layer
            encoding_layers: List of neurons in encoding layers
            threshold_percentile: Percentile for anomaly threshold (default 95th)
        """
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.encoding_layers = encoding_layers
        self.threshold_percentile = threshold_percentile
        self.model = None
        self.threshold = None
        self.scaler = StandardScaler()
        self.history = None
        
    def build_model(self):
        """Build autoencoder architecture"""
        # Encoder
        encoder_input = layers.Input(shape=(self.input_dim,), name='encoder_input')
        x = encoder_input
        
        for units in self.encoding_layers:
            x = layers.Dense(units, activation='relu')(x)
            x = layers.BatchNormalization()(x)
            x = layers.Dropout(0.2)(x)
        
        # Latent layer (bottleneck)
        latent = layers.Dense(self.latent_dim, activation='relu', name='latent')(x)
        
        # Decoder (mirror of encoder)
        x = latent
        for units in reversed(self.encoding_layers):
            x = layers.Dense(units, activation='relu')(x)
            x = layers.BatchNormalization()(x)
            x = layers.Dropout(0.2)(x)
        
        # Output layer
        decoder_output = layers.Dense(self.input_dim, activation='linear', name='decoder_output')(x)
        
        # Complete autoencoder
        self.model = Model(inputs=encoder_input, outputs=decoder_output, name='autoencoder')
        
        # Compile
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        logger.info(f"Autoencoder built: {self.input_dim} -> {self.encoding_layers} -> {self.latent_dim} -> {self.encoding_layers[::-1]} -> {self.input_dim}")
        
    def train(self, X_train: np.ndarray, epochs: int = 100, batch_size: int = 32,
              validation_split: float = 0.2, verbose: int = 0) -> Dict:
        """
        Train autoencoder on normal data
        
        Args:
            X_train: Training data (assumed to be mostly normal)
            epochs: Training epochs
            batch_size: Batch size
            validation_split: Validation split ratio
            verbose: Verbosity level
            
        Returns:
            Training history dict
        """
        # Scale data
        X_scaled = self.scaler.fit_transform(X_train)
        
        # Build model if not exists
        if self.model is None:
            self.build_model()
        
        # Train (autoencoder reconstructs its own input)
        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        self.history = self.model.fit(
            X_scaled, X_scaled,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[early_stop],
            verbose=verbose
        )
        
        # Calculate reconstruction errors on training data
        reconstructions = self.model.predict(X_scaled, verbose=0)
        mse = np.mean(np.square(X_scaled - reconstructions), axis=1)
        
        # Set threshold at specified percentile
        self.threshold = np.percentile(mse, self.threshold_percentile)
        
        logger.info(f"Autoencoder trained: {len(self.history.history['loss'])} epochs")
        logger.info(f"Anomaly threshold set at {self.threshold_percentile}th percentile: {self.threshold:.4f}")
        
        return {
            'epochs': len(self.history.history['loss']),
            'final_loss': float(self.history.history['loss'][-1]),
            'threshold': float(self.threshold)
        }
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies
        
        Args:
            X: Input data
            
        Returns:
            Tuple of (anomaly_scores, is_anomaly)
            anomaly_scores: Reconstruction error for each sample
            is_anomaly: Boolean array indicating anomalies
        """
        if self.model is None:
            raise ValueError("Model not trained")
        
        # Scale and reconstruct
        X_scaled = self.scaler.transform(X)
        reconstructions = self.model.predict(X_scaled, verbose=0)
        
        # Calculate reconstruction error (MSE per sample)
        anomaly_scores = np.mean(np.square(X_scaled - reconstructions), axis=1)
        
        # Flag anomalies
        is_anomaly = anomaly_scores > self.threshold
        
        return anomaly_scores, is_anomaly
    
    def save(self, filepath: Path):
        """Save model and scaler"""
        filepath = Path(filepath)
        self.model.save(str(filepath.with_suffix('.h5')))
        joblib.dump({
            'scaler': self.scaler,
            'threshold': self.threshold,
            'config': {
                'input_dim': self.input_dim,
                'latent_dim': self.latent_dim,
                'encoding_layers': self.encoding_layers,
                'threshold_percentile': self.threshold_percentile
            }
        }, str(filepath.with_suffix('.pkl')))
        logger.info(f"Autoencoder saved to {filepath}")
    
    def load(self, filepath: Path):
        """Load model and scaler"""
        filepath = Path(filepath)
        self.model = keras.models.load_model(str(filepath.with_suffix('.h5')))
        data = joblib.load(str(filepath.with_suffix('.pkl')))
        self.scaler = data['scaler']
        self.threshold = data['threshold']
        self.input_dim = data['config']['input_dim']
        self.latent_dim = data['config']['latent_dim']
        self.encoding_layers = data['config']['encoding_layers']
        self.threshold_percentile = data['config']['threshold_percentile']
        logger.info(f"Autoencoder loaded from {filepath}")


class PCAAnomalyDetector:
    """
    PCA for dimensionality reduction and anomaly detection.
    Anomalies have high reconstruction error when projected back from principal components.
    """
    
    def __init__(self, n_components: float = 0.95, threshold_percentile: float = 95.0):
        """
        Initialize PCA detector
        
        Args:
            n_components: Number of components or variance ratio to retain (0-1)
            threshold_percentile: Percentile for anomaly threshold
        """
        self.n_components = n_components
        self.threshold_percentile = threshold_percentile
        self.pca = PCA(n_components=n_components)
        self.scaler = StandardScaler()
        self.threshold = None
        
    def train(self, X_train: np.ndarray) -> Dict:
        """
        Fit PCA on training data
        
        Args:
            X_train: Training data
            
        Returns:
            Training metrics dict
        """
        # Scale data
        X_scaled = self.scaler.fit_transform(X_train)
        
        # Fit PCA
        self.pca.fit(X_scaled)
        
        # Calculate reconstruction errors on training data
        X_transformed = self.pca.transform(X_scaled)
        X_reconstructed = self.pca.inverse_transform(X_transformed)
        reconstruction_errors = np.mean(np.square(X_scaled - X_reconstructed), axis=1)
        
        # Set threshold
        self.threshold = np.percentile(reconstruction_errors, self.threshold_percentile)
        
        logger.info(f"PCA trained: {self.pca.n_components_} components explain {self.pca.explained_variance_ratio_.sum()*100:.2f}% variance")
        logger.info(f"Anomaly threshold: {self.threshold:.4f}")
        
        return {
            'n_components': int(self.pca.n_components_),
            'explained_variance': float(self.pca.explained_variance_ratio_.sum()),
            'threshold': float(self.threshold)
        }
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies using reconstruction error
        
        Args:
            X: Input data
            
        Returns:
            Tuple of (anomaly_scores, is_anomaly)
        """
        if self.threshold is None:
            raise ValueError("Model not trained")
        
        # Scale, transform, and reconstruct
        X_scaled = self.scaler.transform(X)
        X_transformed = self.pca.transform(X_scaled)
        X_reconstructed = self.pca.inverse_transform(X_transformed)
        
        # Calculate reconstruction error
        anomaly_scores = np.mean(np.square(X_scaled - X_reconstructed), axis=1)
        
        # Flag anomalies
        is_anomaly = anomaly_scores > self.threshold
        
        return anomaly_scores, is_anomaly
    
    def get_principal_components(self, X: np.ndarray) -> np.ndarray:
        """Transform data to principal component space"""
        X_scaled = self.scaler.transform(X)
        return self.pca.transform(X_scaled)
    
    def save(self, filepath: Path):
        """Save PCA model"""
        joblib.dump({
            'pca': self.pca,
            'scaler': self.scaler,
            'threshold': self.threshold,
            'config': {
                'n_components': self.n_components,
                'threshold_percentile': self.threshold_percentile
            }
        }, filepath)
        logger.info(f"PCA detector saved to {filepath}")
    
    def load(self, filepath: Path):
        """Load PCA model"""
        data = joblib.load(filepath)
        self.pca = data['pca']
        self.scaler = data['scaler']
        self.threshold = data['threshold']
        self.n_components = data['config']['n_components']
        self.threshold_percentile = data['config']['threshold_percentile']
        logger.info(f"PCA detector loaded from {filepath}")


class OneClassSVMAnomalyDetector:
    """
    One Class SVM for novelty detection.
    Learns decision boundary around normal data; samples outside are anomalies.
    """
    
    def __init__(self, nu: float = 0.05, kernel: str = 'rbf', gamma: str = 'scale'):
        """
        Initialize One Class SVM
        
        Args:
            nu: Upper bound on fraction of outliers (training errors) and lower bound on support vectors
            kernel: Kernel type ('rbf', 'linear', 'poly', 'sigmoid')
            gamma: Kernel coefficient
        """
        self.nu = nu
        self.kernel = kernel
        self.gamma = gamma
        self.model = OneClassSVM(nu=nu, kernel=kernel, gamma=gamma)
        self.scaler = StandardScaler()
        
    def train(self, X_train: np.ndarray) -> Dict:
        """
        Fit One Class SVM
        
        Args:
            X_train: Training data (normal samples)
            
        Returns:
            Training metrics dict
        """
        # Scale data
        X_scaled = self.scaler.fit_transform(X_train)
        
        # Fit model
        self.model.fit(X_scaled)
        
        # Get decision scores on training data
        decision_scores = self.model.decision_function(X_scaled)
        predictions = self.model.predict(X_scaled)
        
        n_outliers = np.sum(predictions == -1)
        outlier_ratio = n_outliers / len(X_train)
        
        logger.info(f"One Class SVM trained: {n_outliers}/{len(X_train)} ({outlier_ratio*100:.2f}%) training outliers")
        logger.info(f"Decision score range: [{decision_scores.min():.4f}, {decision_scores.max():.4f}]")
        
        return {
            'n_support_vectors': int(self.model.n_support_[0]),
            'training_outliers': int(n_outliers),
            'outlier_ratio': float(outlier_ratio),
            'decision_score_min': float(decision_scores.min()),
            'decision_score_max': float(decision_scores.max())
        }
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies
        
        Args:
            X: Input data
            
        Returns:
            Tuple of (anomaly_scores, is_anomaly)
            anomaly_scores: Negative of decision function (higher = more anomalous)
            is_anomaly: Boolean array
        """
        # Scale data
        X_scaled = self.scaler.transform(X)
        
        # Predict (-1 for outliers, 1 for inliers)
        predictions = self.model.predict(X_scaled)
        decision_scores = self.model.decision_function(X_scaled)
        
        # Convert to anomaly scores (higher = more anomalous)
        # Decision function returns negative values for outliers
        anomaly_scores = -decision_scores
        
        # Flag anomalies
        is_anomaly = predictions == -1
        
        return anomaly_scores, is_anomaly
    
    def save(self, filepath: Path):
        """Save model"""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'config': {
                'nu': self.nu,
                'kernel': self.kernel,
                'gamma': self.gamma
            }
        }, filepath)
        logger.info(f"One Class SVM saved to {filepath}")
    
    def load(self, filepath: Path):
        """Load model"""
        data = joblib.load(filepath)
        self.model = data['model']
        self.scaler = data['scaler']
        self.nu = data['config']['nu']
        self.kernel = data['config']['kernel']
        self.gamma = data['config']['gamma']
        logger.info(f"One Class SVM loaded from {filepath}")


class IsolationForestAnomalyDetector:
    """
    Isolation Forest for anomaly detection.
    Isolates anomalies by randomly partitioning data; anomalies require fewer partitions.
    Robust to high-dimensional data and scales well.
    """
    
    def __init__(self, n_estimators: int = 100, contamination: float = 0.05, 
                 max_samples: str = 'auto', random_state: int = 42):
        """
        Initialize Isolation Forest
        
        Args:
            n_estimators: Number of isolation trees
            contamination: Expected proportion of outliers
            max_samples: Number of samples per tree
            random_state: Random seed
        """
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.max_samples = max_samples
        self.random_state = random_state
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            max_samples=max_samples,
            random_state=random_state
        )
        self.scaler = StandardScaler()
        
    def train(self, X_train: np.ndarray) -> Dict:
        """
        Fit Isolation Forest
        
        Args:
            X_train: Training data
            
        Returns:
            Training metrics dict
        """
        # Scale data
        X_scaled = self.scaler.fit_transform(X_train)
        
        # Fit model
        self.model.fit(X_scaled)
        
        # Get predictions on training data
        predictions = self.model.predict(X_scaled)
        anomaly_scores = -self.model.score_samples(X_scaled)  # Higher = more anomalous
        
        n_outliers = np.sum(predictions == -1)
        outlier_ratio = n_outliers / len(X_train)
        
        logger.info(f"Isolation Forest trained: {self.n_estimators} trees")
        logger.info(f"Detected {n_outliers}/{len(X_train)} ({outlier_ratio*100:.2f}%) outliers in training data")
        logger.info(f"Anomaly score range: [{anomaly_scores.min():.4f}, {anomaly_scores.max():.4f}]")
        
        return {
            'n_estimators': int(self.n_estimators),
            'training_outliers': int(n_outliers),
            'outlier_ratio': float(outlier_ratio),
            'anomaly_score_min': float(anomaly_scores.min()),
            'anomaly_score_max': float(anomaly_scores.max())
        }
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies
        
        Args:
            X: Input data
            
        Returns:
            Tuple of (anomaly_scores, is_anomaly)
        """
        # Scale data
        X_scaled = self.scaler.transform(X)
        
        # Predict (-1 for outliers, 1 for inliers)
        predictions = self.model.predict(X_scaled)
        
        # Get anomaly scores (higher = more anomalous)
        anomaly_scores = -self.model.score_samples(X_scaled)
        
        # Flag anomalies
        is_anomaly = predictions == -1
        
        return anomaly_scores, is_anomaly
    
    def save(self, filepath: Path):
        """Save model"""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'config': {
                'n_estimators': self.n_estimators,
                'contamination': self.contamination,
                'max_samples': self.max_samples,
                'random_state': self.random_state
            }
        }, filepath)
        logger.info(f"Isolation Forest saved to {filepath}")
    
    def load(self, filepath: Path):
        """Load model"""
        data = joblib.load(filepath)
        self.model = data['model']
        self.scaler = data['scaler']
        self.n_estimators = data['config']['n_estimators']
        self.contamination = data['config']['contamination']
        self.max_samples = data['config']['max_samples']
        self.random_state = data['config']['random_state']
        logger.info(f"Isolation Forest loaded from {filepath}")


class EnsembleAnomalyDetector:
    """
    Ensemble detector combining all four methods.
    Aggregates results using voting or weighted average.
    """
    
    def __init__(self, X_sample: np.ndarray, voting: str = 'majority'):
        """
        Initialize ensemble
        
        Args:
            X_sample: Sample data to determine input dimensions
            voting: Voting method ('majority', 'unanimous', 'any', 'weighted')
        """
        self.voting = voting
        input_dim = X_sample.shape[1]
        
        # Initialize all detectors
        self.autoencoder = AutoencoderAnomalyDetector(input_dim=input_dim, latent_dim=max(8, input_dim // 4))
        self.pca = PCAAnomalyDetector(n_components=0.95)
        self.svm = OneClassSVMAnomalyDetector(nu=0.05)
        self.isolation_forest = IsolationForestAnomalyDetector(contamination=0.05)
        
        self.detectors = {
            'autoencoder': self.autoencoder,
            'pca': self.pca,
            'svm': self.svm,
            'isolation_forest': self.isolation_forest
        }
        
    def train(self, X_train: np.ndarray) -> Dict:
        """Train all detectors"""
        results = {}
        
        logger.info("Training Ensemble Anomaly Detector...")
        
        # Train Autoencoder
        logger.info("\n[1/4] Training Autoencoder...")
        results['autoencoder'] = self.autoencoder.train(X_train, epochs=50, verbose=0)
        
        # Train PCA
        logger.info("[2/4] Training PCA...")
        results['pca'] = self.pca.train(X_train)
        
        # Train One Class SVM
        logger.info("[3/4] Training One Class SVM...")
        results['svm'] = self.svm.train(X_train)
        
        # Train Isolation Forest
        logger.info("[4/4] Training Isolation Forest...")
        results['isolation_forest'] = self.isolation_forest.train(X_train)
        
        logger.info("\nEnsemble training complete!")
        
        return results
    
    def predict(self, X: np.ndarray) -> Dict:
        """
        Detect anomalies using ensemble
        
        Args:
            X: Input data
            
        Returns:
            Dict with results from each detector and ensemble decision
        """
        results = {}
        
        # Get predictions from each detector
        for name, detector in self.detectors.items():
            scores, is_anomaly = detector.predict(X)
            results[name] = {
                'anomaly_scores': scores,
                'is_anomaly': is_anomaly,
                'n_anomalies': int(np.sum(is_anomaly)),
                'anomaly_ratio': float(np.mean(is_anomaly))
            }
        
        # Ensemble voting
        anomaly_votes = np.stack([
            results['autoencoder']['is_anomaly'],
            results['pca']['is_anomaly'],
            results['svm']['is_anomaly'],
            results['isolation_forest']['is_anomaly']
        ], axis=0)
        
        if self.voting == 'majority':
            # At least 2 out of 4 vote anomaly
            ensemble_anomaly = np.sum(anomaly_votes, axis=0) >= 2
        elif self.voting == 'unanimous':
            # All 4 must agree
            ensemble_anomaly = np.all(anomaly_votes, axis=0)
        elif self.voting == 'any':
            # At least 1 votes anomaly
            ensemble_anomaly = np.any(anomaly_votes, axis=0)
        elif self.voting == 'weighted':
            # Weighted by normalized scores
            scores_normalized = np.stack([
                (results['autoencoder']['anomaly_scores'] - results['autoencoder']['anomaly_scores'].min()) / 
                (results['autoencoder']['anomaly_scores'].max() - results['autoencoder']['anomaly_scores'].min() + 1e-10),
                (results['pca']['anomaly_scores'] - results['pca']['anomaly_scores'].min()) / 
                (results['pca']['anomaly_scores'].max() - results['pca']['anomaly_scores'].min() + 1e-10),
                (results['svm']['anomaly_scores'] - results['svm']['anomaly_scores'].min()) / 
                (results['svm']['anomaly_scores'].max() - results['svm']['anomaly_scores'].min() + 1e-10),
                (results['isolation_forest']['anomaly_scores'] - results['isolation_forest']['anomaly_scores'].min()) / 
                (results['isolation_forest']['anomaly_scores'].max() - results['isolation_forest']['anomaly_scores'].min() + 1e-10)
            ], axis=0)
            ensemble_score = np.mean(scores_normalized, axis=0)
            ensemble_anomaly = ensemble_score > 0.5
        else:
            raise ValueError(f"Unknown voting method: {self.voting}")
        
        results['ensemble'] = {
            'is_anomaly': ensemble_anomaly,
            'n_anomalies': int(np.sum(ensemble_anomaly)),
            'anomaly_ratio': float(np.mean(ensemble_anomaly)),
            'voting_method': self.voting
        }
        
        return results
    
    def save(self, directory: Path):
        """Save all detectors"""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        self.autoencoder.save(directory / 'autoencoder')
        self.pca.save(directory / 'pca.pkl')
        self.svm.save(directory / 'svm.pkl')
        self.isolation_forest.save(directory / 'isolation_forest.pkl')
        
        joblib.dump({'voting': self.voting}, directory / 'ensemble_config.pkl')
        logger.info(f"Ensemble saved to {directory}")
    
    def load(self, directory: Path):
        """Load all detectors"""
        directory = Path(directory)
        
        self.autoencoder.load(directory / 'autoencoder')
        self.pca.load(directory / 'pca.pkl')
        self.svm.load(directory / 'svm.pkl')
        self.isolation_forest.load(directory / 'isolation_forest.pkl')
        
        config = joblib.load(directory / 'ensemble_config.pkl')
        self.voting = config['voting']
        logger.info(f"Ensemble loaded from {directory}")
