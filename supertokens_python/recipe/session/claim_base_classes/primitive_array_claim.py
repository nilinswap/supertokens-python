# Copyright (c) 2021, VRAI Labs and/or its affiliates. All rights reserved.
#
# This software is licensed under the Apache License, Version 2.0 (the
# "License") as published by the Apache Software Foundation.
#
# You may not use this file except in compliance with the License. You may
# obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from typing import Any, Callable, Dict, Optional, TypeVar, Union, Generic, List

from supertokens_python.types import MaybeAwaitable
from supertokens_python.utils import get_timestamp_ms

from ..interfaces import (
    JSONObject,
    JSONPrimitive,
    SessionClaim,
    SessionClaimValidator,
    ClaimValidationResult,
)


Primitive = TypeVar("Primitive", bound=JSONPrimitive)
PrimitiveList = TypeVar("PrimitiveList", bound=List[JSONPrimitive])

_T = TypeVar("_T")


class SCVMixin(SessionClaimValidator, Generic[_T]):
    def __init__(
        self,
        id_: str,
        claim: SessionClaim[PrimitiveList],
        val: _T,
        max_age_in_sec: int,  # TODO: Default 5 min
    ):
        super().__init__(id_)
        self.claim: SessionClaim[PrimitiveList] = claim
        self.val = val
        self.max_age_in_sec = max_age_in_sec

    def should_refetch(
        self,
        payload: JSONObject,
        user_context: Dict[str, Any],
    ) -> bool:
        claim = self.claim

        return (claim.get_value_from_payload(payload, user_context) is None) or (
            self.max_age_in_sec is not None
            and (
                payload[claim.key].get("t", 0)
                < get_timestamp_ms() - self.max_age_in_sec * 1000
            )
        )

    async def _validate(
        self,
        payload: JSONObject,
        user_context: Dict[str, Any],
        is_include: bool,
    ):
        val = self.val
        max_age_in_sec = self.max_age_in_sec

        expected_key = "expectedToInclude" if is_include else "expectedToNotInclude"

        assert isinstance(self.claim, PrimitiveArrayClaim)
        claim_val = self.claim.get_value_from_payload(payload, user_context)

        if claim_val is None:
            return ClaimValidationResult(
                is_valid=False,
                reason={
                    "message": "value does not exist",
                    expected_key: val,
                    "actualValue": claim_val,
                },
            )

        last_refetch_time = self.claim.get_last_refetch_time(payload, user_context)
        assert last_refetch_time is not None
        age_in_sec = (get_timestamp_ms() - last_refetch_time) / 1000
        if max_age_in_sec is not None and age_in_sec > max_age_in_sec:
            return ClaimValidationResult(
                is_valid=False,
                reason={
                    "message": "expired",
                    "ageInSeconds": age_in_sec,
                    "maxAgeInSeconds": max_age_in_sec,
                },
            )

        # Doing this to ensure same code in the upcoming steps irrespective of
        # whether self.val is Primitive or PrimitiveList
        vals: List[JSONPrimitive] = val if isinstance(val, list) else [val]

        claim_val_set = set(claim_val)
        if is_include:
            for v in vals:
                if v not in claim_val_set:
                    return ClaimValidationResult(
                        is_valid=False,
                        reason={
                            "message": "wrong value",
                            expected_key: vals,  # FIXME: Returns a list when val is Primitive whereas
                            # other SDKs return the item itself
                            "actualValue": claim_val,
                        },
                    )
        else:
            for v in vals:
                if v in claim_val_set:
                    return ClaimValidationResult(
                        is_valid=False,
                        reason={
                            "message": "wrong value",
                            expected_key: vals,  # FIXME: Returns a list when val is Primitive whereas
                            # other SDKs return the item itself
                            "actualValue": claim_val,
                        },
                    )

        return ClaimValidationResult(is_valid=True)


class IncludesSCV(SCVMixin[Primitive]):
    async def validate(
        self,
        payload: JSONObject,
        user_context: Dict[str, Any],
    ):
        return await self._validate(payload, user_context, is_include=True)


class ExcludesSCV(SCVMixin[Primitive]):
    async def validate(
        self,
        payload: JSONObject,
        user_context: Dict[str, Any],
    ):
        return await self._validate(payload, user_context, is_include=False)


class IncludesAllSCV(SCVMixin[PrimitiveList]):
    async def validate(
        self,
        payload: JSONObject,
        user_context: Dict[str, Any],
    ):
        return await self._validate(payload, user_context, is_include=True)


class ExcludesAllSCV(SCVMixin[PrimitiveList]):
    async def validate(
        self,
        payload: JSONObject,
        user_context: Dict[str, Any],
    ):
        return await self._validate(payload, user_context, is_include=False)


class PrimitiveArrayClaimValidators(Generic[PrimitiveList]):
    def __init__(
        self, claim: SessionClaim[PrimitiveList], default_max_age_in_sec: int
    ) -> None:
        self.claim = claim
        self.default_max_age_in_sec = default_max_age_in_sec

    def includes(  # pyright: ignore[reportInvalidTypeVarUse]
        self,
        val: Primitive,
        id_: Union[str, None] = None,
        max_age_in_seconds: Optional[int] = None,
    ) -> SessionClaimValidator:
        max_age_in_sec = max_age_in_seconds or self.default_max_age_in_sec
        return IncludesSCV(
            (id_ or self.claim.key), self.claim, val=val, max_age_in_sec=max_age_in_sec
        )

    def excludes(  # pyright: ignore[reportInvalidTypeVarUse]
        self,
        val: Primitive,
        id_: Union[str, None] = None,
        max_age_in_seconds: Optional[int] = None,
    ) -> SessionClaimValidator:
        max_age_in_sec = max_age_in_seconds or self.default_max_age_in_sec
        return ExcludesSCV(
            (id_ or self.claim.key), self.claim, val=val, max_age_in_sec=max_age_in_sec
        )

    def includes_all(
        self,
        val: PrimitiveList,
        id_: Union[str, None] = None,
        max_age_in_seconds: Optional[int] = None,
    ) -> SessionClaimValidator:
        max_age_in_sec = max_age_in_seconds or self.default_max_age_in_sec
        return IncludesAllSCV(
            (id_ or self.claim.key), self.claim, val=val, max_age_in_sec=max_age_in_sec
        )

    def excludes_all(
        self,
        val: PrimitiveList,
        id_: Union[str, None] = None,
        max_age_in_seconds: Optional[int] = None,
    ) -> SessionClaimValidator:
        max_age_in_sec = max_age_in_seconds or self.default_max_age_in_sec
        return ExcludesAllSCV(
            (id_ or self.claim.key), self.claim, val=val, max_age_in_sec=max_age_in_sec
        )


class PrimitiveArrayClaim(SessionClaim[PrimitiveList]):
    def __init__(
        self,
        key: str,
        fetch_value: Callable[
            [str, Dict[str, Any]],
            MaybeAwaitable[Optional[PrimitiveList]],
        ],
        default_max_age_in_sec: Optional[int] = None,
    ) -> None:
        super().__init__(key, fetch_value)

        claim = self
        self.validators = PrimitiveArrayClaimValidators(
            claim, default_max_age_in_sec or 300
        )  # 5 min

    def add_to_payload_(
        self,
        payload: Dict[str, Any],
        value: PrimitiveList,
        user_context: Union[Dict[str, Any], None] = None,
    ) -> JSONObject:
        payload[self.key] = {"v": value, "t": get_timestamp_ms()}
        _ = user_context

        return payload

    def remove_from_payload_by_merge_(
        self, payload: JSONObject, user_context: Dict[str, Any]
    ) -> JSONObject:
        payload[self.key] = None
        return payload

    def remove_from_payload(
        self, payload: JSONObject, user_context: Dict[str, Any]
    ) -> JSONObject:
        del payload[self.key]
        return payload

    def get_value_from_payload(
        self, payload: JSONObject, user_context: Union[Dict[str, Any], None] = None
    ) -> Union[PrimitiveList, None]:
        _ = user_context

        return payload.get(self.key, {}).get("v")

    def get_last_refetch_time(
        self, payload: JSONObject, user_context: Union[Dict[str, Any], None] = None
    ) -> Union[int, None]:
        _ = user_context

        return payload.get(self.key, {}).get("t")
