import React from "react";

import QRCode from 'qrcode.react';

import "./leftview.css";

import { useState,useEffect } from "react";

import axios from "axios";
import app from "../../firebase/firebase";

import {getDatabase,ref,set,child, onValue} from "firebase/database";
const DetailsCard = ({code, name, description, properties, status, statusMessage }) => {
    return (
      <div className="details-card">
        <h2 className="name">{name}({code})</h2>
        <p className="description">{description}</p>
        {/* <ul className="print-properties">
        {Object.entries(properties).map(([category, options]) => (
        <div key={category} className="property-category">
          <h3 className="category-name">{category}</h3>
          <div className="options-list">
            {options.map((option, index) => (
              <span key={index} className="option">
                {option.name}: {"₹"+option.cost}
                {index < options.length - 1 && ', '}
              </span>
            ))}
          </div>
        </div>
      ))}
        </ul> */}
        <div className="status-container">
            <div className={`status ${status.toLowerCase()=="active"?"active":"inactive"}`}>
                <span className="status-indicator"></span>
                {status}
            </div>
            <p className="status-message">{statusMessage}</p>
        </div>
      </div>
    );
  };

class printerdetails{
    constructor(code,name,description,properties,status,statusMessage) {   
        this.code = code;
        this.name = name;
        this.description = description;
        this.properties = properties;
        this.status = status;
        this.statusMessage = statusMessage;
    }
}

export default function LeftView({ code }) {
  const [printerDetails, setPrinterdetails] = useState(null);

  useEffect(() => {
    if (code == null) {
      return;
    }
    const db = getDatabase(app);
    const printerRef = ref(db, 'Printers/' + code + "/details");

    const unsubscribe = onValue(printerRef, (snapshot) => {
      const data = snapshot.val();
      if (data) {
        setPrinterdetails(new printerdetails(code, data.name, data.description, data.properties, data.status, data.status_message));
      }
    });

    return () => {
      // Cleanup listener
      unsubscribe();
    };
  }, [code]);

  if (!code || !printerDetails) {
    return (
      <div className="loading flex flex-col items-center justify-center h-full w-full">
        <p>Loading Printer Details...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="qrcode">
        <h3>Scan to Print</h3>
        <QRCode
          value={'https://atomte.com/redirect?code=' + code}
          size={250}
          bgColor="#ffffff"
          fgColor="#000000"
          level="H"
          includeMargin={true}
        />
      </div>

      <DetailsCard
        code={code}
        name={printerDetails.name}
        description={printerDetails.description}
        properties={printerDetails.properties}
        status={printerDetails.status}
        statusMessage={printerDetails.statusMessage}
      />
    </div>
  );
}



