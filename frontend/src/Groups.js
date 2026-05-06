import "./index.css";
import { api, apiFetch, apiJson } from "./global.js";
import { useEffect, useState } from "react";
import { useAuth } from "./authContext.js";

/*
A page to display and edit family groups
*/

function Groups({ }) {
    const [ownedGroups, setOwnedGroups] = useState([]);
    const [accessibleGroups, setAccessibleGroups] = useState([]);
    const [shareCode, setShareCode] = useState("");
    const [joinMessage, setJoinMessage] = useState("");

    const { loginKey } = useAuth();

    useEffect(() => {
        async function loadGroups() {
            try {

                const res = await apiFetch("group-access-summary", { loginKey });
                const data = await res.json();

                setOwnedGroups(data.ownedGroups || []);
                setAccessibleGroups(data.accessibleGroups || []);
            } catch (err) {
                console.error("Failed to load groups:", err);
            }
        }

        loadGroups();
    }, []);

    async function handleJoinGroup() {
        try {
            setJoinMessage("");

            await apiJson("share-code/redeem", {
                loginKey,
                method: "POST",
                body: {
                    shareCode: shareCode,
                },
            });

            setShareCode("");
            setJoinMessage("Joined group successfully!");

            // refresh groups
            const data = await apiJson("group-access-summary", { loginKey });
            setOwnedGroups(data.ownedGroups || []);
            setAccessibleGroups(data.accessibleGroups || []);
        } catch (err) {
            console.error(err);
            setJoinMessage("Could not join group. Check the code and try again.");
        }
    }

    async function handleLeaveGroup(groupId) {
        try {
            await apiJson(`family-groups/${groupId}/leave`, {
                loginKey,
                method: "DELETE",
            });

            const data = await apiJson("group-access-summary", { loginKey });
            setOwnedGroups(data.ownedGroups || []);
            setAccessibleGroups(data.accessibleGroups || []);
        } catch (err) {
            console.error("Failed to leave group:", err);
        }
    }

    async function handleRemoveMember(groupId, userId) {
        try {
            await apiJson(`family-groups/${groupId}/members/${userId}`, {
                loginKey,
                method: "DELETE",
            });

            const data = await apiJson("group-access-summary", { loginKey });
            setOwnedGroups(data.ownedGroups || []);
            setAccessibleGroups(data.accessibleGroups || []);
        } catch (err) {
            console.error("Failed to remove member:", err);
        }
    }

    return (
        <div className="group-container">
            <h1>Family Groups</h1>
            <h2>Owned Groups</h2>
            {ownedGroups.map(group => (
                <div key={group.id} className="owned-group-card group-card">
                    <div className="group-field">
                        <span className="field-label">Group</span>
                        <strong>{group.name}</strong>
                    </div>

                    <div className="group-field">
                        <span className="field-label">Share Code</span>
                        <span>{group.shareCode}</span>
                    </div>

                    <div className="group-field members-field">
                        <span className="field-label">Members</span>

                        <div className="members-list">
                            {group.members.map(member => (
                                <div key={member.userId} className="member-row">
                                    <span>{member.username} ({member.role})</span>

                                    {!member.isOwner && (
                                        <button
                                            className="remove-member-btn"
                                            onClick={() => handleRemoveMember(group.id, member.userId)}
                                        >
                                            ×
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            ))}

            <h2>Accessible Groups</h2>
            {accessibleGroups.map(group => (
                <div key={group.id} className="viewer-group-card group-card">
                    <div className="group-field">
                        <span className="field-label">Group</span>
                        <strong>{group.name}</strong>
                    </div>

                    <div className="group-field">
                        <span className="field-label">Owner</span>
                        <span>{group.ownerUsername}</span>
                    </div>

                    <div className="group-field">
                        <span className="field-label">Role</span>
                        <span>{group.myRole}</span>
                    </div>

                    <button
                        className="leave-group-btn"
                        onClick={() => handleLeaveGroup(group.id)}
                    >
                        ×
                    </button>
                </div>
            ))}
            <div className="join-group-box">
                <input
                    type="text"
                    value={shareCode}
                    onChange={(e) => setShareCode(e.target.value)}
                    placeholder="Enter share code"
                />

                <button onClick={handleJoinGroup}>
                    Join Group
                </button>

                {joinMessage && <p>{joinMessage}</p>}
            </div>
        </div>
    );
}

export default Groups;