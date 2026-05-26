import os
import grpc
from fastapi import FastAPI, HTTPException
import node_registry_pb2
import node_registry_pb2_grpc

app = FastAPI()
GRPC_SERVER = os.getenv("GRPC_SERVER", "grpc-server:50051")


def stub():
    channel = grpc.insecure_channel(GRPC_SERVER)
    return node_registry_pb2_grpc.NodeRegistryStub(channel)


@app.post("/nodes")
def register(name: str, address: str):
    resp = stub().Register(node_registry_pb2.RegisterRequest(name=name, address=address))
    return {"id": resp.id, "name": resp.name, "address": resp.address, "status": resp.status, "created_at": resp.created_at}


@app.get("/nodes")
def list_nodes():
    resp = stub().List(node_registry_pb2.Empty())
    return {"nodes": [{"id": n.id, "name": n.name, "address": n.address, "status": n.status, "created_at": n.created_at} for n in resp.nodes]}


@app.get("/nodes/{node_id}")
def get_node(node_id: int):
    try:
        resp = stub().Get(node_registry_pb2.GetRequest(id=node_id))
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(404, "Node not found")
        raise
    return {"id": resp.id, "name": resp.name, "address": resp.address, "status": resp.status, "created_at": resp.created_at}


@app.delete("/nodes/{node_id}")
def delete_node(node_id: int):
    stub().Delete(node_registry_pb2.DeleteRequest(id=node_id))
    return {"message": "Node deleted"}