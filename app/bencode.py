from abc import ABC, abstractmethod
from typing import Any, Generic, Type, TypeVar

from app import const
from app.exceptions import NeedMoreBytesError, WrongBencodeFormatError

T = TypeVar("T")


class Bencode(ABC, Generic[T]):  # noqa: WPS214
    def __init__(self, data: T) -> None:
        if not isinstance(data, self.data_type):
            raise TypeError(f"{self.name}: type(data) = {type(data)} data = {data}")
        self.data: T = data

        self._raw_bytes: bytes = self._to_bytes()

    def __repr__(self) -> str:
        return f"{self.name}({self.data})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.data == other.data

    @property
    def to_bytes(self) -> bytes:
        return self._raw_bytes

    @property
    @abstractmethod
    def to_string(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def data_type(self) -> Type[T]: ...

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> tuple[bytes, "Bencode[Any]"]:
        if len(raw_bytes) < 1:
            raise NeedMoreBytesError
        if raw_bytes[0:1] == const.INTEGER_START:
            return Integer.from_bytes(raw_bytes)
        if raw_bytes[0:1] == const.LIST_START:
            return List.from_bytes(raw_bytes)
        if raw_bytes[0:1] == const.DICT_START:
            return Dict.from_bytes(raw_bytes)
        if chr(raw_bytes[0]).isdigit():
            return String.from_bytes(raw_bytes)
        raise WrongBencodeFormatError(f"Bencode.from_bytes(): raw_bytes = {raw_bytes!r}")

    @abstractmethod
    def _to_bytes(self) -> bytes: ...


class String(Bencode[bytes]):
    @property
    def name(self) -> str:
        return "String"

    @property
    def data_type(self) -> Type[bytes]:
        return bytes

    @property
    def to_string(self) -> str:
        try:
            line = self.data.decode()
        except UnicodeDecodeError:
            line = "UnicodeDecodeError"
        return f'"{line}"'

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> tuple[bytes, "String"]:
        if len(raw_bytes) < 2:
            raise NeedMoreBytesError
        if not chr(raw_bytes[0]).isdigit():
            raise WrongBencodeFormatError(f"String.from_bytes(): raw_bytes = {raw_bytes!r}")
        length_str = ""
        index = 0
        while index < len(raw_bytes) and chr(raw_bytes[index]).isdigit():
            length_str += chr(raw_bytes[index])
            index += 1
        length = int(length_str)
        if index + length > len(raw_bytes):
            raise NeedMoreBytesError
        if raw_bytes[index : index + 1] != const.STRING_DELIMITER:
            raise WrongBencodeFormatError(f"String.from_bytes(): raw_bytes = {raw_bytes!r}")
        result = raw_bytes[index + 1 : index + 1 + length]
        return raw_bytes[index + 1 + length :], String(result)

    def _to_bytes(self) -> bytes:
        return str(len(self.data)).encode() + const.STRING_DELIMITER + self.data


class Integer(Bencode[int]):
    @property
    def name(self) -> str:
        return "Integer"

    @property
    def data_type(self) -> Type[int]:
        return int

    @property
    def to_string(self) -> str:
        return str(self.data)

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> tuple[bytes, "Integer"]:
        if len(raw_bytes) < 3:
            raise NeedMoreBytesError
        if raw_bytes[0:1] != const.INTEGER_START:
            raise WrongBencodeFormatError(f"Integer.from_bytes(): raw_bytes = {raw_bytes!r}")

        result_str = ""
        index = 1
        while index < len(raw_bytes) and raw_bytes[index : index + 1] != const.BENCODE_END:
            result_str += chr(raw_bytes[index])
            index += 1
        if index >= len(raw_bytes):
            raise NeedMoreBytesError
        if raw_bytes[index : index + 1] != const.BENCODE_END:
            raise WrongBencodeFormatError(f"Integer.from_bytes(): raw_bytes = {raw_bytes!r}")
        try:
            result = int(result_str)
        except ValueError:
            raise WrongBencodeFormatError(f"Integer.from_bytes(): raw_bytes = {raw_bytes!r}")
        return raw_bytes[index + 1 :], Integer(result)

    def _to_bytes(self) -> bytes:
        return const.INTEGER_START + str(self.data).encode() + const.BENCODE_END


class List(Bencode[list[Bencode[Any]]]):
    @property
    def name(self) -> str:
        return "List"

    @property
    def data_type(self) -> Type[list[Bencode[Any]]]:
        return list

    @property
    def to_string(self) -> str:
        result: list[str] = []
        for elem in self.data:
            result.append(elem.to_string)
        return "[" + ",".join(result) + "]"

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> tuple[bytes, "Bencode[Any]"]:
        if len(raw_bytes) < 2:
            raise NeedMoreBytesError
        if raw_bytes[0:1] != const.LIST_START:
            raise WrongBencodeFormatError(f"List.from_bytes(): raw_bytes = {raw_bytes!r}")

        raw_bytes = raw_bytes[1:]
        result: list[Bencode[Any]] = []
        while len(raw_bytes) > 1 and raw_bytes[0:1] != const.BENCODE_END:
            raw_bytes, elem = Bencode.from_bytes(raw_bytes)
            result.append(elem)
        if len(raw_bytes) < 1:
            raise NeedMoreBytesError
        if raw_bytes[0:1] != const.BENCODE_END:
            raise WrongBencodeFormatError(f"List.from_bytes(): raw_bytes = {raw_bytes!r}")
        return raw_bytes[1:], List(result)

    def _to_bytes(self) -> bytes:
        result = const.LIST_START
        for elem in self.data:
            result += elem.to_bytes
        return result + const.BENCODE_END


class Dict(Bencode[dict[str, Bencode[Any]]]):
    @property
    def name(self) -> str:
        return "Dict"

    @property
    def data_type(self) -> Type[dict[str, Bencode[Any]]]:
        return dict

    @property
    def to_string(self) -> str:
        result: list[str] = []
        for key in sorted(self.data):
            result.append(f'"{key}":{self.data[key].to_string}')
        return "{" + ",".join(result) + "}"

    @classmethod
    def from_bytes(cls, raw_bytes: bytes) -> tuple[bytes, "Dict"]:
        if len(raw_bytes) < 2:
            raise NeedMoreBytesError
        if raw_bytes[0:1] != const.DICT_START:
            raise WrongBencodeFormatError(f"List.from_bytes(): raw_bytes = {raw_bytes!r}")

        raw_bytes = raw_bytes[1:]
        result: dict[str, Bencode[Any]] = {}
        while len(raw_bytes) > 1 and raw_bytes[0:1] != const.BENCODE_END:
            raw_bytes, key = String.from_bytes(raw_bytes)
            raw_bytes, value = Bencode.from_bytes(raw_bytes)
            result[key.data.decode()] = value
        if len(raw_bytes) < 1:
            raise NeedMoreBytesError
        if raw_bytes[0:1] != const.BENCODE_END:
            raise WrongBencodeFormatError(f"List.from_bytes(): raw_bytes = {raw_bytes!r}")
        return raw_bytes[1:], Dict(result)

    def _to_bytes(self) -> bytes:
        result: list[bytes] = []
        for key, value in self.data.items():
            result.append(key.encode())
            result.append(value.to_bytes)
        return const.DICT_START + b"".join(result) + const.BENCODE_END
