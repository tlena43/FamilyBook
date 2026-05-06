import "./index.css";
import { api } from "./global.js";

/*
A card to display previews with an image and title
*/

function ContentCard({ content }) {
  if (!content) return null;

  const imageSrc = content.fileName
    ? api + "upload/" + content.fileName
    : "/placeholder-image.png"; // fallback if needed

  return (
    <div className="content-card">
      <p>{content.title ?? "Untitled"}</p>
      <img
        src={imageSrc}
        alt={content.title ?? "Content preview"}
      />
    </div>
  );
}

export default ContentCard;