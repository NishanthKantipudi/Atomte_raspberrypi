import React from "react";
import "./rightview.css";
import { get } from "firebase/database";
import { onValue, ref, getDatabase, set, child } from "firebase/database";
import { useState,useEffect } from "react";
import app from "../../firebase/firebase.js";
import ServiceComponent from "./intro.js";




const RightTopView = ({code}) => {
    const [i, setNoInternet] = useState(false);
    const [e, setE] = useState(false);
    const [message, setMessage] = useState('Connecting...');
  const [errorCount, setErrorCount] = useState(0);
  const [isConnected, setIsConnected] = useState(true);
  const [status, setStatus] = useState({});

  useEffect(() => {
    let ws;
    let reconnectInterval;
    let isManualClose = false;  // Flag to control manual close behavior

    

    return () => {
      // When the component is unmounted, manually close the WebSocket and clear the reconnect interval
      isManualClose = true;  // Set the flag to indicate a manual close
      if (ws) {
        ws.close();  // This will trigger ws.onclose, but since it's manual, no reconnection happens
      }
      clearInterval(reconnectInterval);
    };
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await fetch('http://localhost:5000/status');
      const data = await response.json();
      console.log(data);
      if(data["data"]=="internet not connected"){
          setNoInternet(true)
      }else{
          setNoInternet(false)
      }
      setStatus(data);
    } catch (error) {
      console.error("Error fetching status:", error);
    }
  };

  // Fetch status on component mount and every 5 seconds
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(() => {
      fetchStatus();
    }, 5000); // Poll every 5 seconds
    return () => clearInterval(interval); // Clean up interval on component unmount
  }, []);

    const [printermessage,setPrintermessage] = useState(null);
    const [queuecount,setQueuecount] = useState(null);
    useEffect(() => {
        onValue(ref(getDatabase(app), 'Printers/'+code+"/details/message"), (snapshot) => {
            const data=snapshot.val();
	    if(data){
            setPrintermessage(data.value);}
        })
    },[]);
    useEffect(() => {
        onValue(ref(getDatabase(app), 'Printers/'+code+"/printstodo"), (snapshot) => {
            if(snapshot.val()){
            const data=Object.keys(snapshot.val()).length;
            setQueuecount(data);}
        })
    },[]);
    const [userPrintdata,setUserPrintdata] = useState(null);
    const [userPrintdata1,setUserPrintdata1] = useState(null);
    const [fileData,setFileData]=useState(null)
    const [fileData1,setFileData1]=useState(null)
    useEffect(() => {
        onValue(ref(getDatabase(app), 'Printers/'+code+"/printstodo"), (snapshot) => {
            setFileData(null)
            const data=snapshot.val();
            if(data){
                const curr=Object.values(data)[0]
                const user=curr.user
                if(curr.files){
                    const files=curr.files.split(",")
                    const currentprintingfile=curr.printing
                    const currentprintingfile1=curr.done_printing+1
                    get(ref(getDatabase(app), 'users/'+user+'/details')).then((snapshot) => {

                        setUserPrintdata(new userprintdata(snapshot.child("name").val(),snapshot.child("atomte_id").val(),files.length,currentprintingfile-1))
                        setUserPrintdata1(new userprintdata(snapshot.child("name").val(),snapshot.child("atomte_id").val(),files.length,currentprintingfile1-1))
                    })
                    set(ref(getDatabase(app), 'Printers/'+code+"/nowprint/id"),Object.keys(data)[0])
                    setFileData(null)
                    setFileData1(null)
                    onValue(ref(getDatabase(app), 'users/'+user+'/printsdetails/'+files[currentprintingfile-1]), (snapshot) => {
                        const filesdata=snapshot.val()
			                  if(filesdata){
                        setFileData(filesdata)}
        
                    })
                    onValue(ref(getDatabase(app), 'users/'+user+'/printsdetails/'+files[currentprintingfile1-1]), (snapshot) => {
                        const filesdata=snapshot.val()
                        if(filesdata){
                        setFileData1(filesdata)}
                    })
                }
            }
        })
    },[]);
    const ProgressBar = ({ progress,text }) => {
      return (
        <div className="progress-container">
          <div className="progress-bar" style={{ width: `${progress}%` }}>
            <span className="progress-text">{`${text}`}</span>
          </div>
        </div>
      );
    };
      const FeedbackMessage = () => {
        return (
            <div className="feedback-container">
                <div className="feedback-card">
                    <div className="emoji">😊</div>
                    <h1>Thank You!</h1>
                    <p>We're thrilled to hear you enjoyed using our service!</p>
                    <p>Your satisfaction is our top priority.</p>
                </div>
            </div>
        );
    }
    if(i || e){
	return(
		<div style={{ padding: '20px', backgroundColor: '#ffdddd', color: '#d8000c', textAlign: 'center' }}>
          <h3>No Internet Connection </h3>
          <p>Please check your network settings and try again.</p>
        </div>
	);

    }

    if(fileData){
        return (
            <div className="container">
                <div className="message">
                    <h2>{printermessage}</h2>
                </div>
                <div className="queue-count">Total {queuecount} members are in queue</div>
                <hr></hr>
                <div className="print-details">
                    <div className="username">Hello, {userPrintdata.username} ({userPrintdata.id})</div>
                    <hr></hr>
                    <h3>Downloaded files({userPrintdata.totaldone+1+"/"+userPrintdata.totalfiles})</h3>
                    <div className="file-details">
                        <div className="total-files">No of Files : {userPrintdata.totalfiles}</div>
                        <div className="done-count">Done : {userPrintdata.totaldone}</div>
                        <div className="left-count">Left : {userPrintdata.left}</div>
                    </div>
                    
                    <div className="now-printing">
                        <h3>Now downloading...</h3>
                        <div className="file-name">File Name : {fileData.name}</div>
                        <div className="status">Status : {fileData.status}</div>
                        <ProgressBar progress={fileData.printprogress} text={fileData.printprogress?fileData.printprogress:0+"%"} />
                        <h3>Properties</h3>
                        <div className="properties">
                        {Object.entries(fileData.properties).map(([key, value]) => (
                            <div className="property" key={key}>
                                {key.charAt(0).toUpperCase() + key.slice(1)}: {value}
                            </div>
                            ))}
                        </div>
                    </div>
                    {fileData1 ?<div>
                      <hr></hr>
                    <h3>Printed files({userPrintdata1.totaldone+1+"/"+userPrintdata1.totalfiles})</h3>
                    <div className="file-details">
                        <div className="total-files">No of Files : {userPrintdata1.totalfiles}</div>
                        <div className="done-count">Done : {userPrintdata1.totaldone}</div>
                        <div className="left-count">Left : {userPrintdata1.left}</div>
                    </div>
                    <div className="now-printing">
                        <h3>Now printing...</h3>
                        <div className="file-name">File Name : {fileData1.name}</div>
                        <div className="status">Status : {fileData1.status}</div>
                        <ProgressBar text={fileData1.printed} progress={fileData1.printed?(fileData1.printed.split("/")[0]/fileData1.printed.split("/")[1])*100:0} />
                        <h3>Properties</h3>
                        <div className="properties">
                        {Object.entries(fileData1.properties).map(([key, value]) => (
                            <div className="property" key={key}>
                                {key.charAt(0).toUpperCase() + key.slice(1)}: {value}
                            </div>
                            ))}
                        </div>
                    </div>
                    </div>:<></>}
                    
    
                </div>
    
            </div>
        ); 
    }else{
        return (<ServiceComponent></ServiceComponent>)
    }
    
};

class userprintdata{
    constructor(username,id,totalfiles,totaldone) {
        this.username = username;
        this.id = id;
        this.totalfiles = totalfiles;
        this.totaldone = totaldone;
        this.left = this.totalfiles-this.totaldone;
    }
}

export default RightTopView