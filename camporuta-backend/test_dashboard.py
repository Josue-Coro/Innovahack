import sys
import os
from datetime import datetime, date, time
from fastapi.testclient import TestClient

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from database import SessionLocal
import models

def test_dashboard_endpoints():
    client = TestClient(app)
    db = SessionLocal()
    
    try:
        print("=== STARTING DASHBOARD ENDPOINTS TEST (v3.0) ===")
        
        # Test legacy metrics
        print("\nTesting GET /dashboard/metrics...")
        response = client.get("/dashboard/metrics")
        assert response.status_code == 200
        data = response.json()
        print("Metrics:", data)
        assert "total_rutas" in data
        assert "total_visitas" in data
        
        # Get active reponedor and date from database to check actual endpoints
        rep = db.query(models.Usuario).filter(models.Usuario.id_rol == 3).first()
        if rep:
            test_fecha = "2026-05-30"
            print(f"\nTesting GET /dashboard/metricas/{test_fecha}...")
            response = client.get(f"/dashboard/metricas/{test_fecha}")
            assert response.status_code == 200
            print("Dashboard Metrics Status: 200 OK")
            
            print(f"\nTesting GET /dashboard/reponedor/{rep.id_usuario}/{test_fecha}...")
            response = client.get(f"/dashboard/reponedor/{rep.id_usuario}/{test_fecha}")
            assert response.status_code == 200
            print("Reponedor Metrics Status: 200 OK")
            
            print(f"\nTesting GET /reporte/exportar/{test_fecha}...")
            response = client.get(f"/reporte/exportar/{test_fecha}")
            assert response.status_code == 200
            assert response.headers["Content-Disposition"] == f"attachment; filename=reporte_{test_fecha}.csv"
            print("Export Report Status: 200 OK")

        # Test weather endpoint
        test_lat, test_lon = -16.5000, -68.1500  # La Paz
        print(f"\nTesting GET /clima/{test_lat}/{test_lon}...")
        response = client.get(f"/clima/{test_lat}/{test_lon}")
        assert response.status_code == 200
        weather_data = response.json()
        print("Weather Data:", weather_data)
        assert "temperatura" in weather_data
        assert "descripcion" in weather_data

        print("\n=== ALL DASHBOARD TESTS PASSED SUCCESSFULLY! ===")
        
    except Exception as e:
        print("ERROR:", e)
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    test_dashboard_endpoints()
