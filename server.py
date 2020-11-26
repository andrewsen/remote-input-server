import socket
import grpc
import netifaces
import uinput

from zeroconf import ServiceInfo, IPVersion, Zeroconf
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Tuple, Optional

import service_pb2_grpc
from service_pb2 import ConnectDataMsg, ConnectResponseMsg, Empty, ScrollDataMsg, MouseDataMsg, ButtonDataMsg


class RemoteInputServer(service_pb2_grpc.RemoteInputServiceServicer):
    def __init__(self, device: uinput.Device):
        self._device = device

    def SendConnectData(self, request: ConnectDataMsg, context: grpc.ServicerContext):
        print(f"Connect data received, code: {request.check}")
        return ConnectResponseMsg(check=request.check)

    def SendScrollData(self, request: ScrollDataMsg, context: grpc.ServicerContext):
        if request.valueX != 0:
            self._device.emit(uinput.REL_HWHEEL, request.valueX)
        if request.valueY != 0:
            self._device.emit(uinput.REL_WHEEL, request.valueY)
        return Empty()

    def SendMouseData(self, request: MouseDataMsg, context: grpc.ServicerContext):
        self._device.emit(uinput.REL_X, request.deltaX, syn=False)
        self._device.emit(uinput.REL_Y, request.deltaY)
        return Empty()

    def SendButtonData(self, request: ButtonDataMsg, context: grpc.ServicerContext):
        print(f"Button data received, id: {request.button}, pressed: {request.pressed}")

        pressed = 1 if request.pressed else 0

        if request.button == 1:
            self._device.emit(uinput.BTN_LEFT, pressed)
        elif request.button == 2:
            self._device.emit(uinput.BTN_RIGHT, pressed)
        elif request.button == 3:
            self._device.emit(uinput.BTN_MIDDLE, pressed)
        elif request.button == 201:
            self._device.emit(uinput.KEY_VOLUMEUP, pressed)
        elif request.button == 202:
            self._device.emit(uinput.KEY_VOLUMEDOWN, pressed)
        return Empty()


def serve(device: uinput.Device):
    server = grpc.server(ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_RemoteInputServiceServicer_to_server(RemoteInputServer(device), server)
    server.add_insecure_port("[::]:17863")
    server.start()
    server.wait_for_termination()


def get_ip() -> Optional[str]:
    for iface in netifaces.interfaces():
        for record in netifaces.ifaddresses(iface).values():
            if len(record) > 0 and record[0]["addr"].startswith("192.168."):
                return record[0]["addr"]
    return None


def register_zeroconf_service() -> Tuple[Zeroconf, ServiceInfo]:
    ip = get_ip()

    if not ip:
        raise ValueError("Can't obtain IP address")

    info = ServiceInfo(
        "_grpc._tcp.local.",
        f"Input Server ({socket.gethostname()})._grpc._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=17863
    )

    zeroconf = Zeroconf(ip_version=IPVersion.All)
    zeroconf.register_service(info)
    return zeroconf, info


def unregister_zeroconf_service(zeroconf: Zeroconf, info: ServiceInfo):
    zeroconf.unregister_service(info)
    zeroconf.close()


def main():
    with uinput.Device([
        uinput.REL_WHEEL, uinput.REL_HWHEEL,
        uinput.REL_X, uinput.REL_Y,
        uinput.BTN_LEFT, uinput.BTN_MIDDLE, uinput.BTN_RIGHT,
        uinput.KEY_VOLUMEUP, uinput.KEY_VOLUMEDOWN
    ]) as device:
        zeroconf, info = register_zeroconf_service()
        serve(device)
        unregister_zeroconf_service(zeroconf, info)


if __name__ == "__main__":
    main()
