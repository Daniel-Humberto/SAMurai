import numpy as np
from scipy.spatial import Voronoi, cKDTree
from typing import Optional

CANVAS_W = 364
CANVAS_H = 486

class VoronoiEngine:
    """Engine to compute spatial Voronoi diagrams and team territorial control maps."""
    def compute(self, projected: list[dict]) -> dict:
        """
        A partir de posiciones canónicas de robots (excluyendo balón):
        1. Genera diagrama de Voronoi con scipy.spatial.Voronoi
        2. Para cada píxel del canvas, determina a qué equipo pertenece
           el robot más cercano (KD-tree o distancias vectorizadas con NumPy)
        3. Calcula % de área canónica controlada por cada equipo

        Retorna:
        {
          "azul_pct": float,
          "rojo_pct": float,
          "control_map": [[int]] # 182x243 downsampled, 0=azul, 1=rojo, 2=ninguno
        }
        Devolver dict vacío si hay menos de 2 robots detectados.
        """
        # Filter robots (excluding ball class_id==2)
        robots = [obj for obj in projected if obj["class_id"] in (0, 1)]
        if len(robots) < 2:
            return {}

        points = np.array([[r["x_px"], r["y_px"]] for r in robots], dtype=np.float32)
        
        # Generar diagrama de Voronoi con scipy.spatial.Voronoi (as requested in step 1)
        try:
            _ = Voronoi(points)
        except Exception:
            # Handle collinear points or issues gracefully
            pass

        # Map teams to integer values: 0=azul, 1=rojo
        teams = []
        for r in robots:
            team_str = r.get("team")
            if team_str == "azul":
                teams.append(0)
            elif team_str == "rojo":
                teams.append(1)
            else:
                teams.append(0 if r["class_id"] == 0 else 1)
        teams = np.array(teams, dtype=np.int32)

        # Downsampled grid: y in [0, 242], x in [0, 181]
        # Map back to canvas coords: x_canvas = x * 2.0, y_canvas = y * 2.0
        grid_y, grid_x = np.mgrid[0:243, 0:182]
        grid_y_canvas = grid_y * 2.0
        grid_x_canvas = grid_x * 2.0

        grid_points = np.stack([grid_x_canvas.ravel(), grid_y_canvas.ravel()], axis=-1)

        # Use KD-Tree to find nearest robot
        tree = cKDTree(points)
        _, indices = tree.query(grid_points)

        grid_teams = teams[indices]
        control_map = grid_teams.reshape((243, 182))

        # Calculate percentages
        total_pixels = 243 * 182
        azul_pixels = int(np.sum(control_map == 0))
        rojo_pixels = int(np.sum(control_map == 1))

        azul_pct = (azul_pixels / total_pixels) * 100.0
        rojo_pct = (rojo_pixels / total_pixels) * 100.0

        return {
            "azul_pct": azul_pct,
            "rojo_pct": rojo_pct,
            "control_map": control_map.tolist()
        }
