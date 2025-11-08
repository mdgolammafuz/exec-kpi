import { useEffect, useState } from "react";
import
  {
    runSQL,
    getABSample,
    runABTest,
    trainML,
    latestML,
} from "./api";
  
import type {
  KPIResponse,
  ABSampleResponse,
  ABTestResult,
} from "./api";

type Tab = "kpi" | "ab" | "ml";

function App ()
{
  const [ tab, setTab ] = useState<Tab>( "kpi" );
  const [ output, setOutput ] = useState<unknown>( null );
  const [ error, setError ] = useState<string | null>( null );

  return (
    <div style={ { maxWidth: 1100, margin: "0 auto", padding: "1.5rem" } }>
      <h1>ExecKPI — Data Gov UI</h1>
      <p style={ { color: "#555" } }>React client talking to FastAPI.</p>

      <div style={ { display: "flex", gap: "0.5rem", marginBottom: "1rem" } }>
        <button onClick={ () => setTab( "kpi" ) } disabled={ tab === "kpi" }>
          KPI
        </button>
        <button onClick={ () => setTab( "ab" ) } disabled={ tab === "ab" }>
          A/B
        </button>
        <button onClick={ () => setTab( "ml" ) } disabled={ tab === "ml" }>
          ML
        </button>
      </div>

      { tab === "kpi" && (
        <KPIPanel setOutput={ setOutput } setError={ setError } />
      ) }
      { tab === "ab" && <ABPanel setOutput={ setOutput } setError={ setError } /> }
      { tab === "ml" && <MLPanel setOutput={ setOutput } setError={ setError } /> }

      <h2 style={ { marginTop: "1.5rem" } }>Result</h2>
      { error ? (
        <pre
          style={ {
            background: "#ffefef",
            padding: "1rem",
            border: "1px solid #e99",
          } }
        >
          { error }
        </pre>
      ) : (
        <pre
          style={ {
            background: "#111",
            color: "#0f0",
            padding: "1rem",
            minHeight: "150px",
            overflow: "auto",
          } }
        >
          { output ? JSON.stringify( output, null, 2 ) : "No output yet." }
        </pre>
      ) }
    </div>
  );
}

function KPIPanel ( {
  setOutput,
  setError,
}: {
  setOutput: ( d: KPIResponse ) => void;
  setError: ( m: string | null ) => void;
} )
{
  const [ start, setStart ] = useState<string>( () =>
    new Date( Date.now() - 30 * 86400000 ).toISOString().slice( 0, 10 )
  );
  const [ end, setEnd ] = useState<string>( () =>
    new Date().toISOString().slice( 0, 10 )
  );
  const [ sqlFile, setSqlFile ] = useState<string>( "01_vw_revenue_daily.sql" );

  const fetchKPI = () =>
  {
    setError( null );
    runSQL( sqlFile, [
      { name: "start", type: "DATE", value: start },
      { name: "end", type: "DATE", value: end },
    ] )
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
        setError( err instanceof Error ? err.message : "Request failed" )
      );
  };

  return (
    <div>
      <h2>KPI</h2>
      <div style={ { display: "flex", gap: "0.5rem", marginBottom: "0.5rem" } }>
        <label>
          SQL:
          <select
            value={ sqlFile }
            onChange={ ( e ) => setSqlFile( e.target.value ) }
            style={ { marginLeft: "0.25rem" } }
          >
            <option value="01_vw_revenue_daily.sql">
              01_vw_revenue_daily.sql
            </option>
            <option value="24_vw_ab_metrics.sql">24_vw_ab_metrics.sql</option>
            <option value="03_vw_retention_weekly.sql">
              03_vw_retention_weekly.sql
            </option>
          </select>
        </label>
        <label>
          Start:
          <input
            type="date"
            value={ start }
            onChange={ ( e ) => setStart( e.target.value ) }
          />
        </label>
        <label>
          End:
          <input
            type="date"
            value={ end }
            onChange={ ( e ) => setEnd( e.target.value ) }
          />
        </label>
        <button onClick={ fetchKPI }>Run</button>
      </div>
    </div>
  );
}

function ABPanel ( {
  setOutput,
  setError,
}: {
  setOutput: ( d: ABSampleResponse | ABTestResult ) => void;
  setError: ( m: string | null ) => void;
} )
{
  const [ sample, setSample ] = useState<
    ABSampleResponse[ "sample" ] | null
  >( null );
  const [ alpha, setAlpha ] = useState<number>( 0.05 );

  useEffect( () =>
  {
    getABSample()
      .then( ( data ) =>
      {
        setSample( data.sample );
        setOutput( data );
      } )
      .catch( ( err: unknown ) =>
        setError( err instanceof Error ? err.message : "Request failed" )
      );
  }, [ setError, setOutput ] );

  const runTest = () =>
  {
    if ( !sample?.A || !sample?.B ) return;
    setError( null );
    runABTest( {
      a_success: sample.A.success,
      a_total: sample.A.total,
      b_success: sample.B.success,
      b_total: sample.B.total,
      alpha,
    } )
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
        setError( err instanceof Error ? err.message : "Request failed" )
      );
  };

  return (
    <div>
      <h2>A/B</h2>
      { sample ? (
        <>
          <p>
            A: { sample.A.success }/{ sample.A.total } | B: { sample.B.success }/
            { sample.B.total }
          </p>
          <label>
            alpha:
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="0.2"
              value={ alpha }
              onChange={ ( e ) => setAlpha( parseFloat( e.target.value ) ) }
            />
          </label>
          <button onClick={ runTest } style={ { marginLeft: "0.5rem" } }>
            Run test
          </button>
        </>
      ) : (
        <p>Loading sample…</p>
      ) }
    </div>
  );
}

function MLPanel ( {
  setOutput,
  setError,
}: {
  setOutput: ( d: unknown ) => void;
  setError: ( m: string | null ) => void;
} )
{
  const [ target, setTarget ] = useState<string>( "label" );

  const handleTrain = () =>
  {
    setError( null );
    trainML( target )
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
        setError( err instanceof Error ? err.message : "Request failed" )
      );
  };

  const handleLatest = () =>
  {
    setError( null );
    latestML()
      .then( ( data ) => setOutput( data ) )
      .catch( ( err: unknown ) =>
        setError( err instanceof Error ? err.message : "Request failed" )
      );
  };

  return (
    <div>
      <h2>ML</h2>
      <label>
        Target:
        <input
          value={ target }
          onChange={ ( e ) => setTarget( e.target.value ) }
          style={ { marginLeft: "0.25rem" } }
        />
      </label>
      <button onClick={ handleTrain } style={ { marginLeft: "0.5rem" } }>
        Train
      </button>
      <button onClick={ handleLatest } style={ { marginLeft: "0.5rem" } }>
        Latest
      </button>
      <p style={ { color: "#777" } }>
        Note: backend ML is a placeholder until Gold features are confirmed.
      </p>
    </div>
  );
}

export default App;
