import numpy as np
from collections import deque
from typing import Optional
from filterpy.kalman import KalmanFilter

HISTORY_LEN = 30  # frames de historial para forecast

class TrajectoryForecaster:
    """Kalman Filter-based forecaster for short-horizon target trajectory prediction."""
    def __init__(self, fps: float = 30.0, horizon_frames: int = 15):
        self.fps = fps
        self.horizon = horizon_frames
        self._histories: dict[int, deque] = {}   # {tracker_id: deque[(x_cm, y_cm)]}
        self._filters: dict[int, KalmanFilter] = {}

    def _init_kalman(self, x: float, y: float) -> KalmanFilter:
        """
        Kalman 2D con estado [x, y, vx, vy].
        Matrices F, H, R, Q estándar para movimiento constante.
        """
        dt = 1.0 / self.fps
        kf = KalmanFilter(dim_x=4, dim_z=2)
        kf.x = np.array([x, y, 0.0, 0.0])  # Initial state
        
        # State transition matrix F
        kf.F = np.array([
            [1.0, 0.0, dt,  0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
        
        # Measurement matrix H
        kf.H = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0]
        ])
        
        # Measurement noise covariance matrix R
        kf.R = np.eye(2) * 5.0
        
        # Process noise covariance matrix Q
        kf.Q = np.array([
            [dt**4 / 4, 0.0, dt**3 / 2, 0.0],
            [0.0, dt**4 / 4, 0.0, dt**3 / 2],
            [dt**3 / 2, 0.0, dt**2, 0.0],
            [0.0, dt**3 / 2, 0.0, dt**2]
        ]) * 10.0
        
        # Covariance matrix P
        kf.P = np.eye(4) * 100.0
        
        return kf

    def update(self, tracker_id: int, x_cm: float, y_cm: float):
        """Actualiza historial y filtro Kalman para este objeto."""
        if tracker_id not in self._histories:
            self._histories[tracker_id] = deque(maxlen=HISTORY_LEN)
        self._histories[tracker_id].append((x_cm, y_cm))

        if tracker_id not in self._filters:
            self._filters[tracker_id] = self._init_kalman(x_cm, y_cm)
        else:
            kf = self._filters[tracker_id]
            kf.predict()
            kf.update(np.array([x_cm, y_cm]))

    def predict(self, tracker_id: int) -> Optional[list[tuple]]:
        """
        Retorna lista de (x_cm, y_cm) para los próximos self.horizon frames.
        Retorna None si historial < 5 frames.
        """
        history = self._histories.get(tracker_id)
        if history is None or len(history) < 5:
            return None

        kf = self._filters.get(tracker_id)
        if kf is None:
            return None

        # Clone current state
        x_pred = kf.x.copy()
        F = kf.F
        
        predictions = []
        for _ in range(self.horizon):
            # Predict step (constant velocity)
            x_pred = np.dot(F, x_pred)
            predictions.append((float(x_pred[0]), float(x_pred[1])))
            
        return predictions

    def all_predictions(self) -> dict:
        """
        {tracker_id: [(x_cm, y_cm), ...] | None}
        para todos los objetos con historial.
        """
        predictions = {}
        for tid in list(self._histories.keys()):
            predictions[tid] = self.predict(tid)
        return predictions

    def histories_json(self) -> dict:
        """
        Serializa el historial completo de posiciones para graficado.
        Retorna {tracker_id: [(x_cm, y_cm), ...]} con listas Python planas.
        """
        return {
            tid: list(deque_)
            for tid, deque_ in self._histories.items()
        }

    def speed_estimates(self) -> dict:
        """
        Velocidad instantánea estimada (cm/s) por objeto.
        Calculada como delta de las dos últimas posiciones × fps.
        Retorna {tracker_id: float}.
        """
        speeds = {}
        for tid, hist in self._histories.items():
            if len(hist) >= 2:
                p1, p2 = hist[-2], hist[-1]
                dist = float(np.hypot(p2[0] - p1[0], p2[1] - p1[1]))
                speeds[tid] = round(dist * self.fps, 2)
            else:
                speeds[tid] = 0.0
        return speeds
