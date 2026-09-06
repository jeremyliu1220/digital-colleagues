# SPDX-License-Identifier: Apache-2.0

FROM node:24.15.0-alpine@sha256:d1b3b4da11eefd5941e7f0b9cf17783fc99d9c6fc34884a665f40a06dbdfc94f AS build
WORKDIR /studio
COPY package.json package-lock.json ./
RUN test "$(node --version)" = "v24.15.0" \
    && test "$(corepack npm --version)" = "11.12.1" \
    && corepack npm ci --ignore-scripts --no-audit
COPY . .
RUN corepack npm run build \
    && printf '%s\n' '{"node":"24.15.0","npm":"11.12.1","schema_version":1}' \
      > dist/build-toolchain.json

FROM nginx:1.29-alpine@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /studio/dist /usr/share/nginx/html
EXPOSE 8080
