import os
import time
import grpc
from concurrent import futures
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
import node_registry_pb2
import node_registry_pb2_grpc

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://noderegistry:noderegistry@db:5432/noderegistry")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)


class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())


def wait_for_db():
    for _ in range(30):
        try:
            engine.connect()
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Could not connect to database")


class NodeRegistryServicer(node_registry_pb2_grpc.NodeRegistryServicer):
    def Register(self, request, context):
        session = SessionLocal()
        node = Node(name=request.name, address=request.address)
        session.add(node)
        session.commit()
        resp = node_registry_pb2.NodeResponse(
            id=node.id, name=node.name, address=node.address,
            status=node.status, created_at=str(node.created_at),
        )
        session.close()
        return resp

    def List(self, request, context):
        session = SessionLocal()
        nodes = session.query(Node).all()
        resp = node_registry_pb2.NodeList(nodes=[
            node_registry_pb2.NodeResponse(
                id=n.id, name=n.name, address=n.address,
                status=n.status, created_at=str(n.created_at),
            ) for n in nodes
        ])
        session.close()
        return resp

    def Get(self, request, context):
        session = SessionLocal()
        node = session.query(Node).get(request.id)
        session.close()
        if not node:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Node not found")
            return node_registry_pb2.NodeResponse()
        return node_registry_pb2.NodeResponse(
            id=node.id, name=node.name, address=node.address,
            status=node.status, created_at=str(node.created_at),
        )

    def Delete(self, request, context):
        session = SessionLocal()
        node = session.query(Node).get(request.id)
        if node:
            session.delete(node)
            session.commit()
        session.close()
        return node_registry_pb2.Empty()


def serve():
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    node_registry_pb2_grpc.add_NodeRegistryServicer_to_server(NodeRegistryServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server listening on :50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()