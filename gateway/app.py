import os
import grpc
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

import node_registry_pb2
import node_registry_pb2_grpc

GRPC_HOST = os.environ.get("GRPC_HOST", "grpc-server:50051")

app = FastAPI(title="Node Registry Gateway")


def get_stub():
    channel = grpc.insecure_channel(GRPC_HOST)
    return node_registry_pb2_grpc.NodeRegistryStub(channel)


class NodeCreate(BaseModel):
    name: str
    host: str
    port: int = Field(gt=0, le=65535)


def node_to_dict(node):
    return {
        "id": node.id,
        "name": node.name,
        "host": node.host,
        "port": node.port,
        "status": node.status,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/nodes", status_code=201)
def register_node(node: NodeCreate):
    stub = get_stub()
    try:
        response = stub.Register(
            node_registry_pb2.RegisterRequest(
                name=node.name,
                host=node.host,
                port=node.port,
            )
        )
        return node_to_dict(response)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.ALREADY_EXISTS:
            raise HTTPException(status_code=409, detail="Node already exists")
        raise HTTPException(status_code=500, detail=str(e.details()))


@app.get("/api/nodes")
def list_nodes():
    stub = get_stub()
    try:
        response = stub.List(node_registry_pb2.Empty())
        return [node_to_dict(n) for n in response.nodes]
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=str(e.details()))


@app.get("/api/nodes/{name}")
def get_node(name: str):
    stub = get_stub()
    try:
        response = stub.Get(node_registry_pb2.GetRequest(name=name))
        return node_to_dict(response)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Node not found")
        raise HTTPException(status_code=500, detail=str(e.details()))


@app.delete("/api/nodes/{name}", status_code=204)
def delete_node(name: str):
    stub = get_stub()
    try:
        stub.Delete(node_registry_pb2.DeleteRequest(name=name))
        return Response(status_code=204)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Node not found")
        raise HTTPException(status_code=500, detail=str(e.details()))
