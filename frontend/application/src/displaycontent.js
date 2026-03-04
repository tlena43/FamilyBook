import React, { useEffect, useState } from "react";
import "./index.css";
import { apiJson } from "./global.js";
import Search from "./search";
import { useAuth } from "./authContext.js";

async function fetchContentOverview(loginKey) {
  const data = await apiJson("content", {
    loginKey,
    method: "GET",
  });

  return data.content;
}

function ProcessContent() {
  const { loginKey } = useAuth();

  const [content, setContent] = useState([]);
  const [loadingContent, setLoadingContent] = useState(true);
  const [errorContent, setErrorContent] = useState(null);

  useEffect(() => {
    if (!loginKey) return;

    let cancelled = false;

    (async () => {
      try {
        setLoadingContent(true);
        setErrorContent(null);

        const valueContent = await fetchContentOverview(loginKey);
        if (cancelled) return;

        setContent(valueContent ?? []);
      } catch (e) {
        if (!cancelled) setErrorContent(e);
      } finally {
        if (!cancelled) setLoadingContent(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [loginKey]);

  return (
    <div>
      {/* Search handles loading/error display now */}
      <Search
        details={content}
        cardType="content"
        isLoading={loadingContent}
        error={errorContent}
      />
    </div>
  );
}

// start display content functions
const DisplayContent = () => {
  return (
    <div>
      <ProcessContent />
    </div>
  );
};
// end display content functions

export default DisplayContent;