"""Simula uma viatura em deslocamento durante a apresentacao, usando o
endpoint POST /posicao ja existente. Com o dashboard aberto em polling,
o marcador do agente anda sozinho no mapa ate o destino.

Uso:
  SALVAI_API_KEY=... python scripts/demo_movimento.py \
      --agente-id 3 --destino-lat -15.8055 --destino-lon -48.1120 --duracao 90
"""
import argparse
import os
import time

import httpx

API_URL = os.environ.get("SALVAI_API_URL", "https://sistema-emergencias-production.up.railway.app")
INTERVALO = 3


def buscar_posicao_atual(client, agente_id):
    resp = client.get(f"{API_URL}/frota")
    resp.raise_for_status()
    for agente in resp.json():
        if agente["id"] == agente_id:
            if agente["latitude"] is None or agente["longitude"] is None:
                raise SystemExit(f"Agente {agente_id} nao tem posicao GPS registrada.")
            return agente["latitude"], agente["longitude"], agente["nome"]
    raise SystemExit(f"Agente id={agente_id} nao encontrado em /frota.")


def enviar_posicao(client, headers, agente_id, lat, lon):
    resp = client.post(
        f"{API_URL}/posicao",
        headers=headers,
        json={"id_agente": agente_id, "lat": lat, "lon": lon},
    )
    resp.raise_for_status()


def main():
    parser = argparse.ArgumentParser(description="Simula deslocamento de uma viatura para demo ao vivo.")
    parser.add_argument("--agente-id", type=int, default=3, help="ID do agente (default 3, Lucas BM - Taguatinga)")
    parser.add_argument("--destino-lat", type=float, default=-15.8055)
    parser.add_argument("--destino-lon", type=float, default=-48.1120)
    parser.add_argument("--duracao", type=int, default=90, help="Duracao total em segundos")
    args = parser.parse_args()

    api_key = os.environ.get("SALVAI_API_KEY")
    if not api_key:
        raise SystemExit("Defina a variavel de ambiente SALVAI_API_KEY antes de rodar.")
    headers = {"X-API-Key": api_key}

    with httpx.Client(timeout=10) as client:
        lat0, lon0, nome = buscar_posicao_atual(client, args.agente_id)
        print(
            f"Agente {args.agente_id} ({nome}) partindo de {lat0:.4f},{lon0:.4f} "
            f"para {args.destino_lat:.4f},{args.destino_lon:.4f} em {args.duracao}s"
        )

        steps = max(1, args.duracao // INTERVALO)
        for i in range(1, steps + 1):
            t = i / steps
            lat = lat0 + (args.destino_lat - lat0) * t
            lon = lon0 + (args.destino_lon - lon0) * t
            enviar_posicao(client, headers, args.agente_id, lat, lon)
            pct = round(t * 100)
            print(f"[{pct:3d}%] posicao enviada: {lat:.6f}, {lon:.6f}")
            if i < steps:
                time.sleep(INTERVALO)

    print("Viatura no local.")


if __name__ == "__main__":
    main()
