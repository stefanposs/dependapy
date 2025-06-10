"""
Type stub for tomllib imported from tomli
This helps with type checking across Python versions
"""

from typing import Any, BinaryIO, Dict, Mapping, Optional, TextIO, Union

def load(fp: BinaryIO, /, *, parse_float: Optional[Any] = None) -> Dict[str, Any]: ...
def loads(s: Union[str, bytes], /, *, parse_float: Optional[Any] = None) -> Dict[str, Any]: ...
