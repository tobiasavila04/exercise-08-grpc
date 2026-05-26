import os
import time
import logging
import grpc
from concurrent import futures
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError

import node_registry_pb2
import node_registry_pb2_grpc

from grpc_health.v1 import health_pb2_grpc, health_pb2
from grpc_health.v1.health import HealthServicer
from grpc_reflection.v1alpha import reflection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# Retry DB connection until Postgres is ready
engine = None
for attempt in range(15):
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect():
            pass
        logger.info("Connected to database")
        break
    except OperationalError:
        logger.info(f"DB not ready (attempt {attempt + 1}/15), retrying in 3s...")
        time.sleep(3)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


Base.metadata.create_all(bind=engine)


class NodeRegistryServicer(node_registry_pb2_grpc.NodeRegistryServicer):
    def _to_proto(self, node):
        return node_registry_pb2.NodeResponse(
            id=node.id,
            name=node.name,
            host=node.host,
            port=node.port,
            status=node.status,
            created_at=node.created_at.isoformat() if node.created_at else "",
            updated_at=node.updated_at.isoformat() if node.updated_at else "",
        )

    def Register(self, request, context):
        db = SessionLocal()
        try:
            existing = db.query(Node).filter(Node.name == request.name).first()
            if existing:
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details("Node already exists")
                return node_registry_pb2.NodeResponse()
            node = Node(name=request.name, host=request.host, port=request.port)
            db.add(node)
            db.commit()
            db.refresh(node)
            logger.info(f"Registered node: {node.name}")
            return self._to_proto(node)
        finally:
            db.close()

    def List(self, request, context):
        db = SessionLocal()
        try:
            nodes = db.query(Node).all()
            return node_registry_pb2.NodeList(nodes=[self._to_proto(n) for n in nodes])
        finally:
            db.close()

    def Get(self, request, context):
        db = SessionLocal()
        try:
            node = db.query(Node).filter(Node.name == request.name).first()
            if not node:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Node not found")
                return node_registry_pb2.NodeResponse()
            return self._to_proto(node)
        finally:
            db.close()

    def Delete(self, request, context):
        db = SessionLocal()
        try:
            node = db.query(Node).filter(Node.name == request.name).first()
            if not node:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Node not found")
                return node_registry_pb2.Empty()
            node.status = "inactive"
            node.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Deleted node: {node.name}")
            return node_registry_pb2.Empty()
        finally:
            db.close()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # NodeRegistry service
    node_registry_pb2_grpc.add_NodeRegistryServicer_to_server(
        NodeRegistryServicer(), server
    )

    # Health check service
    health_servicer = HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set(
        "noderegistry.NodeRegistry", health_pb2.HealthCheckResponse.SERVING
    )

    # Server reflection
    service_names = (
        node_registry_pb2.DESCRIPTOR.services_by_name["NodeRegistry"].full_name,
        health_pb2.DESCRIPTOR.services_by_name["Health"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port("[::]:50051")
    server.start()
    logger.info("gRPC server started on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
