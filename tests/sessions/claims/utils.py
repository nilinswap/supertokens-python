from typing import Dict, Any, Union, Optional

from supertokens_python.framework.request import BaseRequest
from supertokens_python.recipe import session
from supertokens_python.recipe.session import JWTConfig
from supertokens_python.recipe.session.claims import (
    BooleanClaim,
    SessionClaim,
)
from supertokens_python.recipe.session.interfaces import RecipeInterface
from tests.utils import st_init_common_args

TrueClaim = BooleanClaim("st-true", fetch_value=lambda _, __: True)  # type: ignore
NoneClaim = BooleanClaim("st-none", fetch_value=lambda _, __: None)  # type: ignore


def session_functions_override_with_claim(
    claim: SessionClaim[Any], params: Union[Dict[str, Any], None] = None
):
    if params is None:
        params = {}

    def session_function_override(oi: RecipeInterface) -> RecipeInterface:
        oi_create_new_session = oi.create_new_session

        async def new_create_new_session(
            request: BaseRequest,
            user_id: str,
            access_token_payload: Union[None, Dict[str, Any]],
            session_data: Union[None, Dict[str, Any]],
            user_context: Dict[str, Any],
        ):
            payload_update = await claim.build(user_id, user_context)
            if access_token_payload is None:
                access_token_payload = {}
            access_token_payload = {
                **access_token_payload,
                **payload_update,
                **params,
            }

            return await oi_create_new_session(
                request, user_id, access_token_payload, session_data, user_context
            )

        oi.create_new_session = new_create_new_session
        return oi

    return session_function_override


def get_st_init_args(
    claim: SessionClaim[Any] = TrueClaim, jwt: Optional[JWTConfig] = None
):
    return {
        **st_init_common_args,
        "recipe_list": [
            session.init(
                override=session.InputOverrideConfig(
                    functions=session_functions_override_with_claim(claim),
                ),
                jwt=jwt,
            ),
        ],
    }
