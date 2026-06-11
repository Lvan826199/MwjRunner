"""gRPC 协议适配器 — 完整实现。

支持:
- Unary RPC 调用
- Server Streaming RPC
- 动态 proto 反射（无需预编译 stub）
- 元数据（metadata）传递
- TLS / 非 TLS 连接
- 超时控制
"""

from __future__ import annotations

import contextlib
import json
import time
from pathlib import Path
from typing import Any

from mwjrunner.protocols import (
    ProtocolAdapter,
    ProtocolError,
    ProtocolRequest,
    ProtocolResponse,
    ProtocolResult,
)


class GrpcAdapter(ProtocolAdapter):
    """gRPC 协议适配器。"""

    @property
    def protocol_name(self) -> str:
        return "grpc"

    def execute(self, request: ProtocolRequest) -> ProtocolResult:  # noqa: PLR0911 PLR0912 PLR0915
        """执行 gRPC 请求。

        request.target: "host:port/package.Service/Method"
        request.payload: dict (JSON-like message body)
        request.headers: metadata key-value pairs
        request.options:
            - proto_file: str (可选，.proto 文件路径)
            - tls: bool (默认 False)
            - tls_cert: str (CA 证书路径)
            - timeout: float (秒，默认 30)
            - streaming: bool (是否 server streaming)
        """
        try:
            import grpc  # noqa: PLC0415
            from google.protobuf import descriptor_pb2, descriptor_pool, symbol_database  # noqa: PLC0415
            from google.protobuf.json_format import MessageToDict, ParseDict  # noqa: PLC0415
            from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc  # noqa: PLC0415
        except ImportError:
            return ProtocolResult(
                request=request,
                error=ProtocolError(
                    error_type="dependency_missing",
                    message="请安装 grpcio, grpcio-reflection, protobuf: pip install grpcio grpcio-reflection protobuf",
                ),
            )

        start = time.perf_counter()

        # 解析 target
        target = request.target
        parts = target.split("/", 1)
        if len(parts) != 2:
            return ProtocolResult(
                request=request,
                error=ProtocolError(
                    error_type="invalid_target",
                    message=f"target 格式应为 host:port/package.Service/Method，当前: {target}",
                ),
            )

        host = parts[0]
        service_method = parts[1]  # "package.Service/Method"
        sm_parts = service_method.rsplit("/", 1)
        if len(sm_parts) != 2:
            return ProtocolResult(
                request=request,
                error=ProtocolError(
                    error_type="invalid_target",
                    message=f"service/method 格式错误: {service_method}",
                ),
            )

        full_service_name = sm_parts[0]
        method_name = sm_parts[1]

        options = request.options or {}
        use_tls = options.get("tls", False)
        tls_cert = options.get("tls_cert", "")
        timeout = options.get("timeout", 30.0)
        is_streaming = options.get("streaming", False)

        # 建立连接
        try:
            if use_tls:
                if tls_cert:
                    with Path(tls_cert).open("rb") as f:
                        creds = grpc.ssl_channel_credentials(f.read())
                else:
                    creds = grpc.ssl_channel_credentials()
                channel = grpc.secure_channel(host, creds)
            else:
                channel = grpc.insecure_channel(host)
        except Exception as e:
            return ProtocolResult(
                request=request,
                error=ProtocolError(error_type="connection_error", message=str(e)),
            )

        # 使用 server reflection 获取服务描述
        try:
            reflection_stub = reflection_pb2_grpc.ServerReflectionStub(channel)

            # 获取文件描述（响应包含目标文件及其全部传递依赖，必须全部收集）
            file_by_symbol_request = reflection_pb2.ServerReflectionRequest(file_containing_symbol=full_service_name)
            responses = reflection_stub.ServerReflectionInfo(iter([file_by_symbol_request]))
            file_descriptors: list[Any] = []

            for resp in responses:
                if resp.HasField("file_descriptor_response"):
                    for fd_bytes in resp.file_descriptor_response.file_descriptor_proto:
                        fd_proto = descriptor_pb2.FileDescriptorProto()
                        fd_proto.ParseFromString(fd_bytes)
                        file_descriptors.append(fd_proto)
                break

            if not file_descriptors:
                # Fallback: 使用通用 JSON 调用
                return self._generic_call(
                    channel,
                    full_service_name,
                    method_name,
                    request,
                    timeout,
                    is_streaming,
                    start,
                )

            # 按依赖顺序注册全部文件描述（依赖必须先于使用方加入 pool）
            pool = descriptor_pool.DescriptorPool()
            pending = {fd.name: fd for fd in file_descriptors}
            while pending:
                progressed = False
                for fd_name in list(pending):
                    fd = pending[fd_name]
                    if all(dep not in pending for dep in fd.dependency):
                        # 重复/冲突描述跳过
                        with contextlib.suppress(Exception):
                            pool.Add(fd)
                        del pending[fd_name]
                        progressed = True
                if not progressed:
                    # 存在循环或缺失依赖，按原顺序兜底添加
                    for fd in pending.values():
                        with contextlib.suppress(Exception):
                            pool.Add(fd)
                    break

            service_desc = pool.FindServiceByName(full_service_name)
            method_desc = service_desc.FindMethodByName(method_name)

            input_type = method_desc.input_type
            output_type = method_desc.output_type

            # 构建请求消息
            db = symbol_database.Default()
            try:
                request_class = db.GetPrototype(input_type)
                response_class = db.GetPrototype(output_type)
            except KeyError:
                return self._generic_call(
                    channel,
                    full_service_name,
                    method_name,
                    request,
                    timeout,
                    is_streaming,
                    start,
                )

            req_message = ParseDict(request.payload or {}, request_class())

            # 构建 metadata
            metadata = [(k, v) for k, v in (request.headers or {}).items()]

            # 调用
            full_method = f"/{full_service_name}/{method_name}"

            if is_streaming:
                # Server streaming
                responses_data = []
                call = channel.unary_stream(
                    full_method,
                    request_serializer=request_class.SerializeToString,
                    response_deserializer=response_class.FromString,
                )
                for resp_msg in call(req_message, metadata=metadata, timeout=timeout):
                    responses_data.append(MessageToDict(resp_msg))

                elapsed = (time.perf_counter() - start) * 1000
                channel.close()
                return ProtocolResult(
                    request=request,
                    response=ProtocolResponse(
                        status="ok",
                        payload=responses_data,
                        elapsed_ms=elapsed,
                        metadata={"streaming": True, "count": len(responses_data)},
                    ),
                )
            # Unary
            call = channel.unary_unary(
                full_method,
                request_serializer=request_class.SerializeToString,
                response_deserializer=response_class.FromString,
            )
            resp_msg = call(req_message, metadata=metadata, timeout=timeout)
            result_data = MessageToDict(resp_msg)

            elapsed = (time.perf_counter() - start) * 1000
            channel.close()
            return ProtocolResult(
                request=request,
                response=ProtocolResponse(
                    status="ok",
                    payload=result_data,
                    elapsed_ms=elapsed,
                ),
            )

        except grpc.RpcError as e:
            elapsed = (time.perf_counter() - start) * 1000
            channel.close()
            return ProtocolResult(
                request=request,
                response=ProtocolResponse(
                    status="error",
                    payload={"code": e.code().name, "details": e.details()},
                    elapsed_ms=elapsed,
                ),
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            channel.close()
            return ProtocolResult(
                request=request,
                error=ProtocolError(error_type="grpc_error", message=str(e)),
            )

    def _generic_call(
        self,
        channel,
        service_name: str,
        method_name: str,
        request: ProtocolRequest,
        timeout: float,
        is_streaming: bool,
        start: float,
    ) -> ProtocolResult:
        """通用 JSON 编码调用（无 proto 描述时的 fallback）。"""
        try:
            import grpc  # noqa: PLC0415
        except ImportError:
            return ProtocolResult(
                request=request,
                error=ProtocolError(error_type="dependency_missing", message="grpcio not installed"),
            )

        full_method = f"/{service_name}/{method_name}"
        payload_bytes = json.dumps(request.payload or {}).encode("utf-8")
        metadata = [(k, v) for k, v in (request.headers or {}).items()]

        try:
            if is_streaming:
                call = channel.unary_stream(
                    full_method,
                    request_serializer=lambda x: x,
                    response_deserializer=lambda x: json.loads(x) if x else {},
                )
                results = []
                for resp in call(payload_bytes, metadata=metadata, timeout=timeout):
                    results.append(resp)
                elapsed = (time.perf_counter() - start) * 1000
                channel.close()
                return ProtocolResult(
                    request=request,
                    response=ProtocolResponse(
                        status="ok",
                        payload=results,
                        elapsed_ms=elapsed,
                        metadata={"streaming": True, "fallback": True},
                    ),
                )
            call = channel.unary_unary(
                full_method,
                request_serializer=lambda x: x,
                response_deserializer=lambda x: json.loads(x) if x else {},
            )
            resp = call(payload_bytes, metadata=metadata, timeout=timeout)
            elapsed = (time.perf_counter() - start) * 1000
            channel.close()
            return ProtocolResult(
                request=request,
                response=ProtocolResponse(
                    status="ok",
                    payload=resp,
                    elapsed_ms=elapsed,
                    metadata={"fallback": True},
                ),
            )
        except grpc.RpcError as e:
            elapsed = (time.perf_counter() - start) * 1000
            channel.close()
            return ProtocolResult(
                request=request,
                response=ProtocolResponse(
                    status="error",
                    payload={"code": e.code().name, "details": e.details()},
                    elapsed_ms=elapsed,
                ),
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            channel.close()
            return ProtocolResult(
                request=request,
                error=ProtocolError(error_type="grpc_error", message=str(e)),
            )
