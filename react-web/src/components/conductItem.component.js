import React, { Component } from "react";
import PropTypes from "prop-types";

import "./html.component.css"
import "./conductItem.component.css"

function ConductItem(props) {
    var d = new Date(0);
    d.setUTCSeconds(props.lastUpdateTime)
    return (
        <div className="conductItemContainer">
            <div className="conductItem">
                <a className="conductTitle" href={"/conduct/?conductID="+props.id}>
                    {props.name}
                </a>
                <div className="conductRight">
                    <p className="conductLastEdit">
                        Last Edit: {d.toLocaleString()}
                    </p>
                    <a className="conductDeleteLink" onClick={(e) => props.deleteConductClickHandler(e,props.id,props.name)}>
                        Delete
                    </a>
                    <p className="conductRightOptions">
                        /
                    </p>
                    <a className="conductEditLink" href={"/conduct/?conductID=" + props.id + "&edit=True"}>
                        Edit
                    </a>
                </div>
                <p className="conductState">
                    State: {props.state}
                </p>
            </div>       
        </div>
    )
}

export default ConductItem;