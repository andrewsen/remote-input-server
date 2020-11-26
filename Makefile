PYTHON=python

.PHONY: all
all: protobuf

protobuf:
	$(PYTHON) -m grpc_tools.protoc -I./proto/ --python_out=. --grpc_python_out=. ./proto/service.proto

clean:
	rm service_pb2_grpc.py service_pb2.py

