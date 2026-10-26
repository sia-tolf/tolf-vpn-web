"""Read-only VICI inventory; length-delimited parser from TOLF session diagnostics."""
import os
import select
import struct
import time

class ControlError(Exception):
    pass


def decode(data):
    """Decode length-delimited VICI, rejecting duplicate or malformed fields."""
    pos = 0
    root = {}
    stack = [root]
    current_list = None

    def take(n):
        nonlocal pos
        if pos + n > len(data):
            raise ControlError('truncated_message')
        value = data[pos:pos+n]
        pos += n
        return value

    def name():
        return take(take(1)[0]).decode('ascii')

    def value():
        return take(struct.unpack('!H', take(2))[0])

    while pos < len(data):
        kind = take(1)[0]
        if current_list is not None:
            if kind == 5:
                current_list.append(value())
            elif kind == 6:
                current_list = None
            else:
                raise ControlError('invalid_list')
            continue
        if kind == 2:
            if len(stack) == 1:
                raise ControlError('unexpected_section_end')
            stack.pop()
        elif kind in (1, 3, 4):
            key = name()
            if key in stack[-1]:
                raise ControlError('duplicate_field')
            if kind == 3:
                stack[-1][key] = value()
            elif kind == 1:
                child = {}
                stack[-1][key] = child
                stack.append(child)
                if len(stack) > 16:
                    raise ControlError('excessive_depth')
            else:
                current_list = []
                stack[-1][key] = current_list
        else:
            raise ControlError('invalid_element')
    if len(stack) != 1 or current_list is not None:
        raise ControlError('unclosed_message')
    return root


def named(name):
    data = name.encode('ascii')
    return bytes([len(data)]) + data


def encode(fields):
    return b''.join(b'\x03' + named(k) + struct.pack('!H', len(v)) + v
                    for k, v in fields.items())


class Vici:
    def __init__(self, read_fd, write_fd):
        self.read_fd, self.write_fd = read_fd, write_fd
        self.deadline = time.monotonic() + 25
        self.total = 0

    def wait(self, writing=False):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ControlError('transport_timeout')
        ready = select.select([] if writing else [self.read_fd],
                              [self.write_fd] if writing else [], [], remaining)
        if not ready[1 if writing else 0]:
            raise ControlError('transport_timeout')

    def read(self, size):
        output = bytearray()
        while len(output) < size:
            self.wait()
            part = os.read(self.read_fd, size - len(output))
            if not part:
                raise ControlError('transport_closed')
            output.extend(part)
        return bytes(output)

    def send(self, packet):
        data = struct.pack('!I', len(packet)) + packet
        while data:
            self.wait(True)
            written = os.write(self.write_fd, data)
            if not written:
                raise ControlError('transport_closed')
            data = data[written:]

    def receive(self):
        size = struct.unpack('!I', self.read(4))[0]
        self.total += size
        if not 1 <= size <= 512 * 1024 or self.total > 8 * 1024 * 1024:
            raise ControlError('response_too_large')
        return self.read(size)

    def inventory(self):
        self.send(b'\x03' + named('list-sa'))
        if self.receive() != b'\x05':
            raise ControlError('event_registration_failed')
        self.send(b'\x00' + named('list-sas'))
        rows = []
        while True:
            packet = self.receive()
            if packet[0] == 1:
                if decode(packet[1:]) != {}:
                    raise ControlError('invalid_inventory_response')
                break
            prefix = b'\x07' + named('list-sa')
            if not packet.startswith(prefix):
                raise ControlError('unexpected_inventory_event')
            event = decode(packet[len(prefix):])
            if len(event) != 1 or not isinstance(next(iter(event.values())), dict):
                raise ControlError('invalid_inventory_event')
            rows.append(next(iter(event.values())))
            if len(rows) > 10000:
                raise ControlError('too_many_sessions')
        self.send(b'\x04' + named('list-sa'))
        if self.receive() != b'\x05':
            raise ControlError('event_unregistration_failed')
        return rows



