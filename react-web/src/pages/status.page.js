import React, { Component } from "react";

import configData from "./../config/config.json";
import { URL } from"./../utils/api";

import StatusList from "./../components/status.component"

import "./status.page.css"

function apiTriggerStatusRefresh() {
    const requestOptions = {
        method: 'GET',
        credentials: 'include',
    };
    var triggers = fetch(URL()+'models/trigger/all/', requestOptions).then(response => {
        if (response.ok) {
            return response.json()
        }
    }).then(json => {
        return json["results"];
    });
    return triggers
}

export default class StatusPage extends Component {
    constructor(props) {
        super(props);
        this.state = {
            triggers : []
        }

        this.mounted = true;

        this.updateTriggers = this.updateTriggers.bind(this);

        apiTriggerStatusRefresh().then(triggers => {
            this.setState({ triggers : triggers });
            this.updateTriggers();
        })
    }

    componentWillUnmount() {
        this.mounted = false;
    }

    updateTriggers() {
        if (this.mounted) {
            setTimeout(() => {
                apiTriggerStatusRefresh().then(triggers => {
                    this.setState({ triggers : triggers });
                    this.updateTriggers();
                })
            }, 2500 );
        }
    }

    render() {
        return (
            <div className="pageContent1">
                <h1>Trigger Status</h1>
                <br/>
                <div className="pageCenter-outer">
                    <div className="pageCenter-inner">
                        <StatusList triggers={this.state.triggers} />
                    </div>
                </div>
            </div>
        );
    }
}
