import createClient from "openapi-fetch";
import type { paths } from "./generated/schema";

const generatedClient = createClient<paths>();
void generatedClient.GET("/api/author-books");
void generatedClient.GET("/api/author-books/{id}", { params: { path: { id: 12 } } });

// @ts-expect-error The generated contract rejects unknown routes.
void generatedClient.GET("/api/author-books/{slug}", { params: { path: { slug: "title" } } });

// @ts-expect-error The public author-book endpoint has no write operation.
void generatedClient.POST("/api/author-books");

// @ts-expect-error The generated list endpoint accepts no query parameters.
void generatedClient.GET("/api/author-books", { params: { query: { private: true } } });
