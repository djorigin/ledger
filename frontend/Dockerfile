FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* /app/
RUN npm install

COPY . /app/

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
