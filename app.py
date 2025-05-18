from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import networkx as nx
import os

app = Flask(__name__, static_folder='.')

# —————— Load & build graph ——————
def load_graph(csv_path):
    df = pd.read_csv(csv_path)
    G = nx.Graph()

    for _, row in df.iterrows():
        src = row["Source"]
        dst = row["Destination"]
        dist = row["Distance (km)"]
        risk = row["Risk Level"]
        weight = dist + risk * 50

        # add edge with attributes
        G.add_edge(src, dst, Distance=dist, Risk=risk, Weight=weight)

        # attach latitude/longitude to each node
        G.nodes[src]["latitude"] = row["Source_Latitude"]
        G.nodes[src]["longitude"] = row["Source_Longitude"]
        G.nodes[dst]["latitude"] = row["Destination_Latitude"]
        G.nodes[dst]["longitude"] = row["Destination_Longitude"]

    return G

def kruskal_mst(G):
    parent = {n: n for n in G.nodes()}
    rank = {n: 0 for n in G.nodes()}

    def find(u):
        if parent[u] != u:
            parent[u] = find(parent[u])
        return parent[u]

    def union(u, v):
        ru, rv = find(u), find(v)
        if ru == rv:
            return False
        if rank[ru] < rank[rv]:
            parent[ru] = rv
        else:
            parent[rv] = ru
            if rank[ru] == rank[rv]:
                rank[ru] += 1
        return True

    edges = sorted(G.edges(data=True), key=lambda e: e[2]['Weight'])
    T = nx.Graph()
    for u, v, attr in edges:
        if union(u, v):
            T.add_edge(u, v, **attr)
    return T

# — adjust this path to your CSV location —
CSV_PATH = r"M:\daa project\Ecolinkdaanew\DAAdatasetfinal.csv"

G = load_graph(CSV_PATH)


# —————— API: get_corridor ——————
@app.route('/get_corridor')
def get_corridor():
    src = request.args.get('source')
    dst = request.args.get('destination')
    if not src or not dst:
        return jsonify(error="Missing source or destination"), 400

    mst = kruskal_mst(G)
    if src not in mst or dst not in mst:
        return jsonify(error="No path found"), 404

    try:
        node_list = nx.shortest_path(mst, src, dst, weight='Weight')
    except nx.NetworkXNoPath:
        return jsonify(error="No path found"), 404

    # build edge list + totals
    edges = []
    total_distance = 0
    total_risk = 0
    for u, v in zip(node_list, node_list[1:]):
        d = G[u][v]["Distance"]
        r = G[u][v]["Risk"]
        total_distance += d
        total_risk += r
        edges.append({
            "source": u,
            "destination": v,
            "distance": d,
            "risk": r
        })

    # build nodes dict only for the path
    nodes = {
        n: {
            "latitude": G.nodes[n]["latitude"],
            "longitude": G.nodes[n]["longitude"]
        } for n in node_list
    }

    return jsonify({
        "path": edges,
        "nodes": nodes,
        "total_distance": total_distance,
        "total_risk": total_risk
    })


# —————— Serve front-end HTML & static ——————
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/map.html')
def serve_map():
    return send_from_directory('.', 'map.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)




if __name__ == '__main__':
    app.run(debug=True)
