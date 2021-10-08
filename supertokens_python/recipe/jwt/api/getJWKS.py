"""
Copyright (c) 2021, VRAI Labs and/or its affiliates. All rights reserved.

This software is licensed under the Apache License, Version 2.0 (the
"License") as published by the Apache Software Foundation.

You may not use this file except in compliance with the License. You may
obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""
from supertokens_python.recipe.jwt.interfaces import APIInterface
from supertokens_python.recipe.jwt.types import APIOptions
from supertokens_python.utils import send_200_response


async def get_JWKS(api_implementation: APIInterface, options: APIOptions):
    if api_implementation.get_JWKS_GET is None:
        return False

    result = await api_implementation.get_JWKS_GET(options)
    send_200_response({'keys': result.keys}, result.options.response)

    return True
